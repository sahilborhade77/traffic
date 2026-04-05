from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, JSON, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)
Base = declarative_base()

# MODELS (Integrated into DB Access Layer per Part 7)

class Vehicle(Base):
    """RTO Vehicle Registry."""
    __tablename__ = 'vehicles'
    
    plate_number = Column(String(20), primary_key=True)
    owner_name = Column(String(100), nullable=False)
    owner_phone = Column(String(15), nullable=False)
    owner_email = Column(String(100))
    vehicle_type = Column(String(20))
    registration_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)

class Violation(Base):
    """Recorded Traffic Violations."""
    __tablename__ = 'violations'
    
    violation_id = Column(Integer, primary_key=True, autoincrement=True)
    plate_number = Column(String(20))
    violation_type = Column(String(50), nullable=False)
    camera_id = Column(String(50), nullable=False)
    location = Column(String(100), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    
    image_path = Column(String(255))
    video_path = Column(String(255))
    confidence_score = Column(Float)
    
    metadata_json = Column(JSON, name='metadata') # SQL column named 'metadata'
    
    fine_amount = Column(DECIMAL(10, 2))
    fine_status = Column(String(20), default='pending')
    
    reviewed = Column(Boolean, default=False)
    reviewer_notes = Column(String)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class SpeedTracking(Base):
    """Tracking records for Average Speed Enforcement."""
    __tablename__ = 'speed_tracking'
    
    tracking_id = Column(Integer, primary_key=True, autoincrement=True)
    plate_number = Column(String(20))
    entry_camera = Column(String(50), nullable=False)
    entry_timestamp = Column(DateTime, nullable=False)
    exit_camera = Column(String(50))
    exit_timestamp = Column(DateTime)
    
    distance_km = Column(DECIMAL(5, 2))
    time_taken_seconds = Column(Integer)
    average_speed_kmh = Column(DECIMAL(5, 2))
    speed_limit_kmh = Column(Integer)
    
    is_violation = Column(Boolean, default=False)
    violation_id = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.now)

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
