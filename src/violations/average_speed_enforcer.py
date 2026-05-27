import logging
from datetime import datetime
from typing import Dict, Optional
import math

logger = logging.getLogger(__name__)

class AverageSpeedEnforcer:
    """
    Feature: Section Control / Average Speed Enforcement.
    Calculates vehicle speed between two distant cameras (Entry and Exit).
    Formula: Speed = Distance / (Time_Exit - Time_Entry)
    """

    def __init__(self, zone_config: Dict):
        """
        Initialize with zone configuration.
        zone_config = {
            'entry_camera': 'CAM_001',
            'exit_camera': 'CAM_002',
            'distance_km': 2.5,
            'speed_limit_kmh': 60,
            'tolerance_kmh': 5
        }
        """
        self.entry_cam = zone_config['entry_camera']
        self.exit_cam = zone_config['exit_camera']
        self.distance_km = zone_config['distance_km']
        self.speed_limit = zone_config['speed_limit_kmh']
        self.tolerance = zone_config.get('tolerance_kmh', 5)
        
        # In-memory storage for vehicle entry times
        # Key: Plate Number, Value: Entry Timestamp
        self.entry_records: Dict[str, datetime] = {}

    def record_entry(self, plate_number: str, camera_id: str, timestamp: datetime = None):
        """Record a vehicle entering the speed zone."""
        if camera_id != self.entry_cam:
            return
        
        timestamp = timestamp or datetime.now()
        self.entry_records[plate_number] = timestamp
        logger.info(f"Vehicle {plate_number} entered speed zone at {timestamp}")

    def check_exit(self, plate_number: str, camera_id: str, timestamp: datetime = None) -> Optional[Dict]:
        """
        Check if a vehicle exiting the zone has violated the average speed limit.
        Returns violation details if caught, else None.
        """
        if camera_id != self.exit_cam:
            return None
        
        if plate_number not in self.entry_records:
            # Vehicle missed entry camera or started inside zone
            return None
            
        exit_time = timestamp or datetime.now()
        entry_time = self.entry_records.pop(plate_number) # Clear record after exit
        
        time_delta_hours = (exit_time - entry_time).total_seconds() / 3600.0
        
        if time_delta_hours <= 0:
            return None
            
        avg_speed = self.distance_km / time_delta_hours
        
        is_violation = avg_speed > (self.speed_limit + self.tolerance)
        
        if is_violation:
            logger.warning(f"AVERAGE SPEED VIOLATION: {plate_number} | Speed: {avg_speed:.2f} km/h")
            return {
                'plate_number': plate_number,
                'avg_speed': avg_speed,
                'limit': self.speed_limit,
                'distance_km': self.distance_km,
                'entry_time': entry_time,
                'exit_time': exit_time,
                'is_violation': True
            }
            
        return None

    def cleanup_stale_records(self, max_age_hours: int = 1):
        """Remove records that never reached the exit camera."""
        now = datetime.now()
        stale_plates = [
            plate for plate, entry_time in self.entry_records.items()
            if (now - entry_time).total_seconds() / 3600.0 > max_age_hours
        ]
        for plate in stale_plates:
            del self.entry_records[plate]
        if stale_plates:
            logger.info(f"Cleaned up {len(stale_plates)} stale speed zone records.")
