"""
Feature 1: Wrong-Way Driver Detection
--------------------------------------
Uses DeepSORT direction vectors from VehicleTrack.position_history
to determine if a vehicle is moving against expected traffic flow.
No extra VRAM required — uses already-tracked position data.
"""

import numpy as np
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

@dataclass
class WrongWayViolation:
    track_id: int
    plate_number: str
    timestamp: datetime
    measured_angle: float      # Actual direction in degrees
    expected_angle: float      # Allowed direction
    image_path: str
    confidence: float

class WrongWayDetector:
    """
    Detects wrong-way drivers by comparing DeepSORT trajectory direction
    against the expected traffic flow angle for the camera zone.
    Zero extra VRAM — reads from existing track history.
    """
    def __init__(self, expected_flow_angle: float, tolerance_degrees: float = 45.0, min_history: int = 10):
        """
        Args:
            expected_flow_angle: The correct direction of traffic (0-360 degrees).
                                 0=East, 90=South, 180=West, 270=North
            tolerance_degrees:   How many degrees off before flagging (default ±45°)
            min_history:         Minimum position history frames before checking
        """
        self.expected_angle = expected_flow_angle
        self.tolerance = tolerance_degrees
        self.min_history = min_history

        # Track which IDs have already been flagged (avoid duplicates)
        self.flagged_ids: set = set()

        logger.info(f"WrongWayDetector initialized. Expected flow: {expected_flow_angle}°, Tolerance: ±{tolerance_degrees}°")

    def _angle_difference(self, a1: float, a2: float) -> float:
        """Compute smallest angular difference between two directions."""
        diff = abs(a1 - a2) % 360
        return diff if diff <= 180 else 360 - diff

    def check(self, track) -> Optional[WrongWayViolation]:
        """
        Check a VehicleTrack for wrong-way movement.
        
        Args:
            track: VehicleTrack from deepsort_tracker.py
        Returns:
            WrongWayViolation if detected, else None
        """
        if track.track_id in self.flagged_ids:
            return None

        if len(track.position_history) < self.min_history:
            return None  # Not enough data yet

        direction = track.get_average_direction()
        if direction is None:
            return None

        diff = self._angle_difference(direction, self.expected_angle)

        # Wrong way = direction is more than tolerance away from expected
        if diff > (180 - self.tolerance):
            self.flagged_ids.add(track.track_id)
            logger.warning(f"WRONG-WAY VEHICLE: Track {track.track_id} | Angle: {direction:.1f}° vs Expected: {self.expected_angle}°")
            return WrongWayViolation(
                track_id=track.track_id,
                plate_number="",            # Filled by ANPR
                timestamp=datetime.now(),
                measured_angle=direction,
                expected_angle=self.expected_angle,
                image_path="",              # Filled by EvidenceManager
                confidence=min(1.0, diff / 180)
            )
        return None

    def reset_track(self, track_id: int):
        """Remove a track from flagged set when it leaves the scene."""
        self.flagged_ids.discard(track_id)
