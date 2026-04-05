import cv2
import numpy as np
import logging
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional, Set
from datetime import datetime

logger = logging.getLogger(__name__)

class SignalState(Enum):
    """Traffic light signal states."""
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    UNKNOWN = "unknown"

@dataclass
class VehicleDetection:
    """Standardized vehicle detection for the violation engine."""
    track_id: int
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    centroid: Tuple[int, int]
    vehicle_class: str
    confidence: float

@dataclass
class RedLightViolation:
    """Formal record of a red light violation."""
    track_id: int
    plate_number: str
    timestamp: datetime
    signal_state: SignalState
    stop_line_position: int
    vehicle_position: int
    crossing_distance: int
    image_path: str
    confidence: float

class RedLightViolationDetector:
    """
    Enhanced Red Light Violation Detector.
    Features HSV-based signal state detection and 'grandfathering' logic for fair enforcement.
    """
    def __init__(self, config: dict):
        """
        Initialize detector with stop line and ROI configuration.
        """
        self.stop_line_y = config.get('stop_line_y', 450)
        self.violation_threshold = config.get('violation_threshold', 20)
        self.roi = config.get('roi_polygon', None)
        
        # Tracking states
        self.crossed_tracks: Set[int] = set()
        self.grandfathered_tracks: Set[int] = set() # Already past line when light turned red
        
        logger.info(f"RedLightViolationDetector initialized. Stop Line Y: {self.stop_line_y}")

    def detect_signal_state(self, frame: np.ndarray, signal_roi: Tuple[int, int, int, int]) -> SignalState:
        """
        Detect traffic signal state using HSV color analysis.
        """
        if frame is None or frame.size == 0:
            return SignalState.UNKNOWN
            
        x, y, w, h = signal_roi
        signal_crop = frame[y:y+h, x:x+w]
        if signal_crop.size == 0:
            return SignalState.UNKNOWN
            
        hsv = cv2.cvtColor(signal_crop, cv2.COLOR_BGR2HSV)
        
        # HSV Color Ranges
        red_lower1, red_upper1 = np.array([0, 100, 100]), np.array([10, 255, 255])
        red_lower2, red_upper2 = np.array([160, 100, 100]), np.array([180, 255, 255])
        yellow_lower, yellow_upper = np.array([20, 100, 100]), np.array([30, 255, 255])
        green_lower, green_upper = np.array([40, 100, 100]), np.array([80, 255, 255])
        
        # Create masks
        red_mask = cv2.bitwise_or(cv2.inRange(hsv, red_lower1, red_upper1), 
                                 cv2.inRange(hsv, red_lower2, red_upper2))
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        green_mask = cv2.inRange(hsv, green_lower, green_upper)
        
        # Dominant color analysis
        counts = {
            SignalState.RED: cv2.countNonZero(red_mask),
            SignalState.YELLOW: cv2.countNonZero(yellow_mask),
            SignalState.GREEN: cv2.countNonZero(green_mask)
        }
        
        max_state = max(counts, key=counts.get)
        if counts[max_state] < 100: # Sensitivity threshold
            return SignalState.UNKNOWN
            
        return max_state

    def is_vehicle_in_roi(self, vehicle: VehicleDetection) -> bool:
        """Check if vehicle exists within intersection ROI."""
        if self.roi is None:
            return True
        return cv2.pointPolygonTest(self.roi, vehicle.centroid, False) >= 0

    def check_violation(self, vehicle: VehicleDetection, 
                        signal_state: SignalState, 
                        previous_signal_state: SignalState) -> Optional[RedLightViolation]:
        """
        Check for violation with grandfathering logic.
        """
        if signal_state != SignalState.RED:
            self.crossed_tracks.clear()
            self.grandfathered_tracks.clear()
            return None
            
        # Grandfathering: If it just turned red, allow vehicles already past stop line to clear
        if previous_signal_state != SignalState.RED and signal_state == SignalState.RED:
            if vehicle.centroid[1] > self.stop_line_y:
                self.grandfathered_tracks.add(vehicle.track_id)
                logger.debug(f"Track {vehicle.track_id} grandfathered (already past line).")
                
        if vehicle.track_id in self.crossed_tracks or vehicle.track_id in self.grandfathered_tracks:
            return None
            
        # Detect crossing
        crossing_distance = vehicle.centroid[1] - self.stop_line_y
        if crossing_distance > self.violation_threshold:
            self.crossed_tracks.add(vehicle.track_id)
            logger.warning(f"RED LIGHT VIOLATION detected for Track {vehicle.track_id}!")
            
            return RedLightViolation(
                track_id=vehicle.track_id,
                plate_number="", # To be updated by ANPR module
                timestamp=datetime.now(),
                signal_state=signal_state,
                stop_line_position=self.stop_line_y,
                vehicle_position=vehicle.centroid[1],
                crossing_distance=crossing_distance,
                image_path="", # To be updated by Evidence Manager
                confidence=vehicle.confidence
            )
            
        return None

    def draw_visualization(self, frame: np.ndarray, 
                           vehicles: List[VehicleDetection], 
                           signal_state: SignalState) -> np.ndarray:
        """Draw violation logic overlay on the frame."""
        annotated = frame.copy()
        
        # Stop Line
        line_color = (0, 0, 255) if signal_state == SignalState.RED else (0, 255, 0)
        cv2.line(annotated, (0, self.stop_line_y), (frame.shape[1], self.stop_line_y), line_color, 3)
        
        # ROI
        if self.roi is not None:
            cv2.polylines(annotated, [self.roi.astype(np.int32)], True, (255, 255, 0), 2)
            
        for vehicle in vehicles:
            x, y, w, h = vehicle.bbox
            cx, cy = vehicle.centroid
            
            # Color coding
            if cy < self.stop_line_y:
                color = (0, 255, 0) # Safe
            elif vehicle.track_id in self.grandfathered_tracks:
                color = (255, 255, 0) # Grandfathered
            elif vehicle.track_id in self.crossed_tracks:
                color = (0, 0, 255) # Violating
            else:
                color = (255, 165, 0) # Critical
                
            cv2.rectangle(annotated, (x, y), (x+w, y+h), color, 2)
            cv2.circle(annotated, (cx, cy), 5, color, -1)
            cv2.putText(annotated, f"ID:{vehicle.track_id}", (x, y-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
        # Signal State
        state_color = {
            SignalState.RED: (0, 0, 255),
            SignalState.YELLOW: (0, 255, 255),
            SignalState.GREEN: (0, 255, 0),
            SignalState.UNKNOWN: (128, 128, 128)
        }[signal_state]
        
        cv2.putText(annotated, f"SIGNAL: {signal_state.value.upper()}", (20, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, state_color, 3)
                    
        return annotated

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("RedLightViolationDetector loaded.")
