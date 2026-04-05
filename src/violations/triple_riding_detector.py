"""
Feature 2: Triple Riding Detection (Bikes)
-------------------------------------------
Uses the shared YOLO model to count persons on motorcycles.
Flags if 3+ persons are detected on a single 2-wheeler.
VRAM: 0 extra — uses shared model_manager.
"""

import numpy as np
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# COCO class IDs
CLASS_MOTORCYCLE = 3
CLASS_PERSON = 0

@dataclass
class TripleRidingViolation:
    track_id: int
    plate_number: str
    timestamp: datetime
    person_count: int
    image_path: str
    confidence: float

class TripleRidingDetector:
    """
    Detects triple riding by counting persons overlapping each motorcycle bbox.
    Uses shared YOLOv8n model via ModelManager — no extra VRAM.
    """
    def __init__(self, person_overlap_threshold: float = 0.3, max_allowed_riders: int = 2):
        """
        Args:
            person_overlap_threshold: Minimum IoU for a person to be "on" a bike
            max_allowed_riders:       Legal maximum (default 2 for India)
        """
        self.overlap_threshold = person_overlap_threshold
        self.max_riders = max_allowed_riders
        self.flagged_ids: set = set()
        logger.info(f"TripleRidingDetector initialized. Max allowed riders: {max_allowed_riders}")

    def _iou(self, box1, box2) -> float:
        """Compute Intersection over Union between two [x1,y1,x2,y2] boxes."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        inter = max(0, x2 - x1) * max(0, y2 - y1)
        if inter == 0:
            return 0.0
        area1 = (box1[2]-box1[0]) * (box1[3]-box1[1])
        area2 = (box2[2]-box2[0]) * (box2[3]-box2[1])
        return inter / float(area1 + area2 - inter)

    def check(self, frame, track_id: int, bike_bbox: tuple, model_manager) -> Optional[TripleRidingViolation]:
        """
        Run person detection in bike crop and count overlapping persons.
        
        Args:
            frame:         Full camera frame
            track_id:      DeepSORT track ID of the motorcycle
            bike_bbox:     (x1,y1,x2,y2) bounding box of the motorcycle
            model_manager: Shared ModelManager instance
        """
        if track_id in self.flagged_ids:
            return None

        x1, y1, x2, y2 = map(int, bike_bbox)
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        if x2 <= x1 or y2 <= y1:
            return None

        # Use shared YOLO — detect persons only (class 0)
        results = model_manager.detect(frame, conf=0.4, classes=[CLASS_PERSON])
        
        person_count = 0
        for box in results.boxes:
            px1, py1, px2, py2 = box.xyxy[0].cpu().numpy()
            person_box = (px1, py1, px2, py2)
            bike_box = (x1, y1, x2, y2)
            if self._iou(person_box, bike_box) >= self.overlap_threshold:
                person_count += 1

        if person_count > self.max_riders:
            self.flagged_ids.add(track_id)
            logger.warning(f"TRIPLE RIDING: Track {track_id} | {person_count} persons detected on bike!")
            return TripleRidingViolation(
                track_id=track_id,
                plate_number="",
                timestamp=datetime.now(),
                person_count=person_count,
                image_path="",
                confidence=0.85
            )
        return None
