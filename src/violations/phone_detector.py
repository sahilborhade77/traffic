"""
Feature 3: Mobile Phone Detection While Driving
------------------------------------------------
Uses shared YOLOv8n model with class 'cell phone' (COCO class 67)
to detect distracted driving. No extra VRAM needed.

COCO class 67 = 'cell phone'
Strategy: Only check the driver's region (upper-left of vehicle bbox)
"""

import numpy as np
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

CLASS_CELL_PHONE = 67  # COCO dataset class ID

@dataclass
class PhoneViolation:
    track_id: int
    plate_number: str
    timestamp: datetime
    confidence: float
    image_path: str

class PhoneDetector:
    """
    Detects mobile phone usage while driving.
    Crops the driver's area (upper 60% of vehicle bbox) before detection
    to reduce false positives from passengers.
    Uses shared ModelManager — zero extra VRAM.
    """
    def __init__(self, conf_threshold: float = 0.45, cooldown_frames: int = 60):
        """
        Args:
            conf_threshold:  Minimum YOLO confidence to flag
            cooldown_frames: Frames to wait before re-flagging same track
        """
        self.conf_threshold = conf_threshold
        self.cooldown_frames = cooldown_frames
        
        # track_id → last flagged frame number
        self._last_flagged: dict = {}
        self._current_frame = 0
        
        logger.info(f"PhoneDetector initialized. Confidence threshold: {conf_threshold}")

    def check(self, frame, track_id: int, vehicle_bbox: tuple, model_manager, frame_id: int = 0) -> Optional[PhoneViolation]:
        """
        Check driver area of vehicle for mobile phone usage.
        
        Args:
            frame:         Full camera frame
            track_id:      DeepSORT track ID
            vehicle_bbox:  (x1,y1,x2,y2) vehicle bounding box
            model_manager: Shared ModelManager instance
            frame_id:      Current frame number for cooldown
        """
        # Cooldown check — don't re-flag too frequently
        last = self._last_flagged.get(track_id, -999)
        if frame_id - last < self.cooldown_frames:
            return None

        x1, y1, x2, y2 = map(int, vehicle_bbox)
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = max(0,x1), max(0,y1), min(w,x2), min(h,y2)

        if x2 <= x1 or y2 <= y1:
            return None

        # Focus on DRIVER AREA: upper 60%, left 70% of vehicle bbox
        driver_y2 = y1 + int((y2 - y1) * 0.6)
        driver_x2 = x1 + int((x2 - x1) * 0.7)
        driver_crop = frame[y1:driver_y2, x1:driver_x2]

        if driver_crop.size == 0:
            return None

        # Detect cell phone (COCO class 67) using shared model
        results = model_manager.detect(driver_crop, conf=self.conf_threshold, classes=[CLASS_CELL_PHONE])

        if results.boxes and len(results.boxes) > 0:
            best_conf = float(results.boxes[0].conf[0].cpu().numpy())
            self._last_flagged[track_id] = frame_id
            logger.warning(f"PHONE DETECTED: Track {track_id} | Confidence: {best_conf:.2f}")
            return PhoneViolation(
                track_id=track_id,
                plate_number="",
                timestamp=datetime.now(),
                confidence=best_conf,
                image_path=""
            )
        return None
