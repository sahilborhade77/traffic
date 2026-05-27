import logging
from datetime import datetime
from typing import Dict, Optional, List, Tuple
import numpy as np

logger = logging.getLogger(__name__)

class SpeedDetector:
    """
    Detects over-speeding violations using point-based speed estimation.
    Uses pixel-to-meter calibration and vehicle trajectory history.
    """
    def __init__(self, calibration_ppm: float = 10.0, speed_threshold_kmh: float = 60.0, tolerance_kmh: float = 5.0):
        """
        Args:
            calibration_ppm: Pixels Per Meter calibration factor.
            speed_threshold_kmh: Legal speed limit in km/h.
            tolerance_kmh: Allowed margin before flagging violation.
        """
        self.ppm = calibration_ppm
        self.speed_limit = speed_threshold_kmh
        self.tolerance = tolerance_kmh
        self.effective_limit = speed_threshold_kmh + tolerance_kmh
        
        # Track IDs already flagged in current scene to avoid multiple alerts
        self.flagged_ids = set()
        
        logger.info(f"SpeedDetector initialized. Limit: {speed_threshold_kmh} km/h, PPM: {calibration_ppm}")

    def calculate_speed(self, track_history: List[Tuple[float, float, float]]) -> Dict:
        """
        Estimate speed from position history.
        track_history: List of (x, y, timestamp)
        
        Returns: {
            'speed_kmh': float,
            'is_violation': bool,
            'confidence': float
        }
        """
        if len(track_history) < 5:
            return {'speed_kmh': 0.0, 'is_violation': False, 'confidence': 0.0}

        # Use first and last points for a stable estimate
        x1, y1, t1 = track_history[0]
        x2, y2, t2 = track_history[-1]
        
        time_delta = t2 - t1
        if time_delta <= 0:
            return {'speed_kmh': 0.0, 'is_violation': False, 'confidence': 0.0}

        # Euclidean distance in pixels
        dist_px = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        
        # Convert to meters
        dist_m = dist_px / self.ppm
        
        # Speed in m/s
        speed_mps = dist_m / time_delta
        
        # Convert to km/h
        speed_kmh = speed_mps * 3.6
        
        is_violation = speed_kmh > self.effective_limit
        
        # Confidence increases with more history points
        confidence = min(0.95, 0.5 + (len(track_history) / 100))
        
        return {
            'speed_kmh': round(speed_kmh, 2),
            'is_violation': is_violation,
            'confidence': round(confidence, 2)
        }

    def check_violation(self, track_id: int, track_history: List[Tuple[float, float, float]]) -> Optional[Dict]:
        """
        Check if a track is violating speed limits.
        """
        if track_id in self.flagged_ids:
            return None
            
        results = self.calculate_speed(track_history)
        
        if results['is_violation']:
            self.flagged_ids.add(track_id)
            logger.warning(f"SPEED VIOLATION: Track {track_id} | Speed: {results['speed_kmh']} km/h")
            return {
                'track_id': track_id,
                'violation_type': 'OVERSPEEDING',
                'speed_kmh': results['speed_kmh'],
                'speed_limit': self.speed_limit,
                'timestamp': datetime.now(),
                'confidence': results['confidence']
            }
            
        return None

    def reset_track(self, track_id: int):
        """Clean up when vehicle leaves scene."""
        self.flagged_ids.discard(track_id)

if __name__ == "__main__":
    # Unit test
    detector = SpeedDetector(calibration_ppm=10.0, speed_threshold_kmh=60.0)
    # Simulate a car moving 20 meters in 1 second (72 km/h)
    history = [
        (100, 100, 0.0),
        (150, 150, 0.25),
        (200, 200, 0.5),
        (250, 250, 0.75),
        (300, 300, 1.0)
    ]
    # Distance = sqrt(200^2 + 200^2) = 282.8 px = 28.28 meters
    # Speed = 28.28 m/s = 101.8 km/h
    res = detector.calculate_speed(history)
    print(f"Speed Test Result: {res}")
