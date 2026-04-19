import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import models from central models.py
from src.database.models import Base, Vehicle, Violation, SpeedTracking

logger = logging.getLogger(__name__)

# ACCESS LAYER

class ViolationDatabase:
    """
    Unified Database Access Layer for TIS.
    """
    def __init__(self, db_url: str = 'sqlite:///traffic.db'):
        """
        Initialize connection and ensure tables exist.
        """
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self._session = None # Managed lazily or per-call
        logger.info(f"ViolationDatabase session manager ready: {db_url}")
    
    @property
    def session(self):
        if self._session is None:
            self._session = self.Session()
        return self._session

    def create_violation(
        self,
        plate_number: str,
        violation_type: str,
        camera_id: str,
        timestamp: datetime,
        fine_amount: float,
        metadata: Dict,
        image_path: str = None,
        location: str = "Unknown"
    ) -> int:
        """
        Record a new traffic infraction.
        """
        violation = Violation(
            plate_number=plate_number,
            violation_type=violation_type,
            camera_id=camera_id,
            location=location,
            timestamp=timestamp,
            image_path=image_path,
            metadata_json=metadata,
            fine_amount=fine_amount
        )
        
        self.session.add(violation)
        self.session.commit()
        return violation.violation_id
    
    def create_speed_track_entry(
        self,
        plate_number: str,
        entry_camera: str,
        entry_timestamp: datetime,
        distance_km: float,
        speed_limit_kmh: int
    ):
        """
        Start an audit record for a vehicle entering a speed zone.
        """
        track = SpeedTracking(
            plate_number=plate_number,
            entry_camera=entry_camera,
            entry_timestamp=entry_timestamp,
            distance_km=distance_km,
            speed_limit_kmh=speed_limit_kmh
        )
        
        self.session.add(track)
        self.session.commit()
        return track.tracking_id
    
    def complete_speed_track(
        self,
        plate_number: str,
        entry_camera: str,
        exit_camera: str,
        exit_timestamp: datetime,
        average_speed: float,
        is_violation: bool
    ):
        """
        Close a speed record upon exit and store calculated metrics.
        """
        track = self.session.query(SpeedTracking).filter(
            SpeedTracking.plate_number == plate_number,
            SpeedTracking.entry_camera == entry_camera,
            SpeedTracking.exit_timestamp.is_(None)
        ).first()
        
        if track:
            track.exit_camera = exit_camera
            track.exit_timestamp = exit_timestamp
            track.time_taken_seconds = int((exit_timestamp - track.entry_timestamp).total_seconds())
            track.average_speed_kmh = average_speed
            track.is_violation = is_violation
            self.session.commit()
            return True
        return False
    
    def get_vehicle_owner(self, plate_number: str) -> Optional[Dict]:
        """
        Lookup registry for owner contact details.
        """
        vehicle = self.session.query(Vehicle).filter(
            Vehicle.plate_number == plate_number
        ).first()
        
        if vehicle:
            return {
                'name': vehicle.owner_name,
                'phone': vehicle.owner_phone,
                'email': vehicle.owner_email,
                'vehicle_type': vehicle.vehicle_type
            }
        return None
    
    def get_violations_by_plate(self, plate_number: str, days: int = 30) -> List[Violation]:
        """
        Fetch historical records for a specific vehicle.
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        return self.session.query(Violation).filter(
            Violation.plate_number == plate_number,
            Violation.timestamp >= cutoff_date
        ).all()
