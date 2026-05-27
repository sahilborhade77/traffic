from ultralytics import YOLO
import cv2
import torch
import logging
from typing import Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class PlateDetection:
    """Plate detection structure."""
    bbox: Tuple[int, int, int, int] # x,y,w,h
    confidence: float

class PlateDetector:
    """
    ANPR plate detection using a YOLO model when available.
    Falls back to an OpenCV plate-region heuristic when plate weights are missing.
    """
    def __init__(self, model_path='models/yolov8n_plate.pt', use_heuristic_fallback: bool = True):
        """
        Initialize the plate detector.
        """
        self.model = None
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.use_heuristic_fallback = use_heuristic_fallback

        if Path(model_path).exists():
            try:
                self.model = YOLO(model_path).to(self.device)
                if self.device == 'cuda':
                    self.model.half() # Optimized for RTX 2050 (4GB)
                logger.info(f"PlateDetector initialized on {self.device}")
            except Exception as e:
                logger.error(f"Failed to initialize PlateDetector: {e}")
        elif self.use_heuristic_fallback:
            logger.warning(
                "Plate model not found at %s. Using OpenCV heuristic fallback.",
                model_path
            )
        else:
            logger.error(f"Plate model not found: {model_path}")

    def detect(self, vehicle_crop) -> Optional[PlateDetection]:
        """
        Detect plate in vehicle crop. Return single best detection.
        """
        if vehicle_crop is None or vehicle_crop.size == 0:
            return None

        if self.model is None:
            if self.use_heuristic_fallback:
                return self._detect_with_heuristic(vehicle_crop)
            return None
            
        return self._detect_with_model(vehicle_crop)

    def _detect_with_model(self, vehicle_crop) -> Optional[PlateDetection]:
        results = self.model(vehicle_crop, conf=0.4, verbose=False)[0]
        
        if not results.boxes:
            return self._detect_with_heuristic(vehicle_crop) if self.use_heuristic_fallback else None
            
        # Select best detection
        best_box = max(results.boxes, key=lambda x: x.conf[0])
        x1, y1, x2, y2 = best_box.xyxy[0].cpu().numpy().astype(int)
        conf = float(best_box.conf[0].cpu().numpy())
        
        return PlateDetection(
            bbox=(x1, y1, x2 - x1, y2 - y1),
            confidence=conf
        )

    def _detect_with_heuristic(self, vehicle_crop) -> Optional[PlateDetection]:
        """
        Locate a plate-like bright, wide rectangle in a vehicle crop.
        This is a demo fallback, not a substitute for a trained plate model.
        """
        height, width = vehicle_crop.shape[:2]
        if height < 30 or width < 60:
            return None

        if len(vehicle_crop.shape) == 2:
            gray = vehicle_crop
        else:
            gray = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 7, 50, 50)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        candidates = []
        bright_threshold = max(150, int(enhanced.mean() + enhanced.std()))
        bright_mask = cv2.inRange(enhanced, bright_threshold, 255)
        bright_mask = cv2.morphologyEx(
            bright_mask,
            cv2.MORPH_CLOSE,
            cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
        )
        bright_contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        self._add_plate_candidates(bright_contours, candidates, width, height, weight=1.4)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 5))
        blackhat = cv2.morphologyEx(enhanced, cv2.MORPH_BLACKHAT, kernel)

        grad_x = cv2.Sobel(blackhat, cv2.CV_32F, 1, 0, ksize=3)
        grad_x = np_absolute_uint8(grad_x)
        grad_x = cv2.morphologyEx(grad_x, cv2.MORPH_CLOSE, kernel)

        _, thresh = cv2.threshold(grad_x, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        thresh = cv2.erode(thresh, None, iterations=1)
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        self._add_plate_candidates(contours, candidates, width, height)

        if candidates:
            score, x, y, w, h = max(candidates, key=lambda item: item[0])
            return PlateDetection(
                bbox=self._expand_bbox(x, y, w, h, width, height),
                confidence=min(0.65, 0.35 + score * 4.0)
            )

        # Conservative fallback: Indian plates commonly appear around the lower
        # middle of a vehicle crop. Low confidence keeps callers aware it is weak.
        fallback_w = max(60, int(width * 0.48))
        fallback_h = max(18, int(height * 0.13))
        x = max(0, (width - fallback_w) // 2)
        y = min(height - fallback_h, max(0, int(height * 0.58)))
        return PlateDetection(
            bbox=(x, y, min(fallback_w, width - x), min(fallback_h, height - y)),
            confidence=0.15
        )

    def _expand_bbox(self, x: int, y: int, w: int, h: int, width: int, height: int) -> Tuple[int, int, int, int]:
        pad_x = max(2, int(w * 0.08))
        pad_y = max(2, int(h * 0.18))
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(width, x + w + pad_x)
        y2 = min(height, y + h + pad_y)
        return x1, y1, x2 - x1, y2 - y1

    def _add_plate_candidates(self, contours, candidates, width: int, height: int, weight: float = 1.0) -> None:
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if h == 0:
                continue

            aspect = w / float(h)
            area_ratio = (w * h) / float(width * height)
            lower_half_bonus = 1.15 if y > height * 0.35 else 1.0

            if 2.0 <= aspect <= 6.8 and 0.003 <= area_ratio <= 0.18:
                score = area_ratio * lower_half_bonus * weight
                candidates.append((score, x, y, w, h))


def np_absolute_uint8(array):
    min_val, max_val = array.min(), array.max()
    if max_val - min_val < 1e-6:
        return cv2.convertScaleAbs(array)
    scaled = 255 * ((array - min_val) / (max_val - min_val))
    return scaled.astype("uint8")
