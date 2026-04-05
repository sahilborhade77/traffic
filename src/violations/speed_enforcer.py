from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

@dataclass
class SpeedZone:
    """Configuration for an average speed enforcement zone."""
    entry_camera: str
    exit_camera: str
    distance_km: float
    speed_limit_kmh: int
    tolerance_kmh: int = 5  # 5 km/h default tolerance

@dataclass
class VehiclePassage:
    """Record of a vehicle passing a single camera point."""
    plate_number: str
    camera_id: str
    timestamp: datetime
    image_path: str

class AverageSpeedEnforcer:
    """
    Core engine for Average Speed Detection across camera pairs.
    Calculates if a vehicle traveled between two cameras faster than the speed limit.
    """
    def __init__(self, speed_zones: Dict[str, SpeedZone], db_manager):
        """
        Initialize speed enforcement system.
        """
        self.speed_zones = speed_zones
        self.db = db_manager
        
        # In-memory tracking: {plate_number: {entry_camera: VehiclePassage}}
        self.active_tracks: Dict[str, Dict[str, VehiclePassage]] = {}
        
        # Timeout for incomplete tracks (1 hour)
        self.track_timeout = timedelta(hours=1)

    def record_vehicle_passage(self, passage: VehiclePassage):
        """
        Record a vehicle passing through a camera and check for zone transitions.
        """
        plate = passage.plate_number
        camera = passage.camera_id
        
        # Find relevant speed zones for this camera
        entry_zones = [z for z in self.speed_zones.values() if z.entry_camera == camera]
        exit_zones = [z for z in self.speed_zones.values() if z.exit_camera == camera]
        
        # Handle Entry
        if entry_zones:
            self._handle_entry(plate, passage, entry_zones)
        
        # Handle Exit
        if exit_zones:
            self._handle_exit(plate, passage, exit_zones)
        
        # Cleanup expired tracks
        self._cleanup_expired_tracks()

    def _handle_entry(self, plate: str, passage: VehiclePassage, zones: List[SpeedZone]):
        """Vehicle enters one or more speed enforcement zones."""
        if plate not in self.active_tracks:
            self.active_tracks[plate] = {}
        
        for zone in zones:
            self.active_tracks[plate][zone.entry_camera] = passage
            
            # Log to DB (entry point)
            try:
                self.db.create_speed_track_entry(
                    plate_number=plate,
                    entry_camera=zone.entry_camera,
                    entry_timestamp=passage.timestamp,
                    distance_km=zone.distance_km,
                    speed_limit_kmh=zone.speed_limit_kmh
                )
                logger.info(f"Vehicle {plate} logged at entry camera: {zone.entry_camera}")
            except Exception as e:
                logger.error(f"Failed to log entry to DB: {e}")

    def _handle_exit(self, plate: str, passage: VehiclePassage, zones: List[SpeedZone]):
        """Vehicle exits one or more speed enforcement zones."""
        if plate not in self.active_tracks:
            return
        
        for zone in zones:
            if zone.entry_camera not in self.active_tracks[plate]:
                continue
            
            entry_passage = self.active_tracks[plate][zone.entry_camera]
            
            # Calculate speed metrics
            violation_data = self._calculate_speed(entry_passage, passage, zone)
            
            # Update DB (exit point)
            try:
                self.db.complete_speed_track(
                    plate_number=plate,
                    entry_camera=zone.entry_camera,
                    exit_camera=zone.exit_camera,
                    exit_timestamp=passage.timestamp,
                    average_speed=violation_data['avg_speed'],
                    is_violation=violation_data['is_violation']
                )
            except Exception as e:
                logger.error(f"Failed to update speed record in DB: {e}")
            
            # If excessive speed detected, generate formal violation
            if violation_data['is_violation']:
                self._generate_violation(plate, violation_data, entry_passage, passage)
            
            # Clean up active memory track
            del self.active_tracks[plate][zone.entry_camera]
            
            logger.info(
                f"Vehicle {plate} completed zone. Avg Speed: {violation_data['avg_speed']:.1f} km/h "
                f"(Limit: {zone.speed_limit_kmh})"
            )

    def _calculate_speed(self, entry: VehiclePassage, exit: VehiclePassage, zone: SpeedZone) -> Dict:
        """Logic for average speed calculation using entry/exit timestamps."""
        time_diff = (exit.timestamp - entry.timestamp).total_seconds()
        
        if time_diff <= 0:
            return {'avg_speed': 0.0, 'is_violation': False}
        
        # Speed = (Distance in km / Time in hours)
        avg_speed = (zone.distance_km / time_diff) * 3600
        
        # Minimum time required at speed limit
        expected_time = (zone.distance_km / zone.speed_limit_kmh) * 3600
        
        effective_limit = zone.speed_limit_kmh + zone.tolerance_kmh
        is_violation = avg_speed > effective_limit
        
        return {
            'avg_speed': avg_speed,
            'is_violation': is_violation,
            'time_taken_sec': int(time_diff),
            'expected_time_sec': int(expected_time),
            'speed_limit': zone.speed_limit_kmh,
            'effective_limit': effective_limit,
            'distance_km': zone.distance_km
        }

    def _generate_violation(self, plate: str, speed_data: Dict, entry: VehiclePassage, exit: VehiclePassage):
        """Formalize the violation for legal enforcement."""
        excess_speed = speed_data['avg_speed'] - speed_data['speed_limit']
        fine_amount = self._calculate_fine(excess_speed, speed_data['speed_limit'])
        
        metadata = {
            'violation_type': 'average_speed',
            'measured_speed': round(speed_data['avg_speed'], 1),
            'speed_limit': speed_data['speed_limit'],
            'excess_speed': round(excess_speed, 1),
            'distance_km': speed_data['distance_km'],
            'time_taken_sec': speed_data['time_taken_sec'],
            'entry_camera': entry.camera_id,
            'exit_camera': exit.camera_id
        }
        
        try:
            self.db.create_violation(
                plate_number=plate,
                violation_type='OVERSPEEDING_AVERAGE',
                camera_id=f"{entry.camera_id}-{exit.camera_id}",
                timestamp=exit.timestamp,
                fine_amount=fine_amount,
                metadata=metadata,
                image_path=exit.image_path
            )
            logger.warning(f"VIOLATION LOGGED: {plate} | Speed: {speed_data['avg_speed']:.1f} km/h | Fine: RS {fine_amount}")
        except Exception as e:
            logger.error(f"Failed to record formal violation in DB: {e}")

    def _calculate_fine(self, excess_speed: float, speed_limit: int) -> float:
        """Indian MVA progressive penalty structure."""
        if excess_speed <= 10:
            base_fine = 1000
        elif excess_speed <= 20:
            base_fine = 2000
        elif excess_speed <= 30:
            base_fine = 3000
        else:
            base_fine = 5000
        
        if speed_limit >= 80: # Highway multiplier
            base_fine *= 1.5
            
        return round(base_fine, 2)

    def _cleanup_expired_tracks(self):
        """Management of memory to remove vehicles that left the route without exiting zones."""
        now = datetime.now()
        plates_to_remove = []
        
        for plate, cameras in self.active_tracks.items():
            expired_cameras = [cam for cam, passage in cameras.items() if now - passage.timestamp > self.track_timeout]
            for cam in expired_cameras:
                del cameras[cam]
            if not cameras:
                plates_to_remove.append(plate)
                
        for plate in plates_to_remove:
            del self.active_tracks[plate]

if __name__ == "__main__":
    # Placeholder for developer testing
    logging.basicConfig(level=logging.INFO)
    logger.info("AverageSpeedEnforcer module loaded.")
