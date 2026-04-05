from ultralytics import YOLO
import cv2
import torch
import logging
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PlateDetection:
    """Plate detection structure."""
    bbox: Tuple[int, int, int, int] # x,y,w,h
    confidence: float

class PlateDetector:
    """
    ANPR Plate Detection using YOLOv8-tiny.
    Optimized for high-speed detection in vehicle crops.
    """
    def __init__(self, model_path='models/yolov8n_plate.pt'):
        """
        Initialize the YOLOv8-tiny model.
        """
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.model = YOLO(model_path).to(self.device)
            if self.device == 'cuda':
                self.model.half() # Optimized for RTX 2050 (4GB) 
            logger.info(f"PlateDetector initialized on {self.device}")
        except Exception as e:
            logger.error(f"Failed to initialize PlateDetector: {e}")
            self.model = None

    def detect(self, vehicle_crop) -> Optional[PlateDetection]:
        """
        Detect plate in vehicle crop. Return single best detection.
        """
        if self.model is None or vehicle_crop is None or vehicle_crop.size == 0:
            return None
            
        results = self.model(vehicle_crop, conf=0.4, verbose=False)[0]
        
        if not results.boxes:
            return None
            
        # Select best detection
        best_box = max(results.boxes, key=lambda x: x.conf[0])
        x1, y1, x2, y2 = best_box.xyxy[0].cpu().numpy().astype(int)
        conf = float(best_box.conf[0].cpu().numpy())
        
        return PlateDetection(
            bbox=(x1, y1, x2 - x1, y2 - y1),
            confidence=conf
        )
