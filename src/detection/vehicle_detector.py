from ultralytics import YOLO
import cv2
import torch
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

class VehicleDetector:
    """
    Vehicle Detection using YOLOv8.
    Optimized for high-FPS inference.
    """
    def __init__(self, model_path='models/yolov8n.pt'):
        """
        Initialize the YOLOv8 model.
        """
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.model = YOLO(model_path).to(self.device)
            if self.device == 'cuda':
                self.model.half() # Optimized for RTX 2050 (4GB) 
            # Define target classes (COCO)
            self.target_classes = [2, 3, 5, 7] # car, motorcycle, bus, truck
            logger.info(f"VehicleDetector initialized on {self.device}")
        except Exception as e:
            logger.critical(f"Failed to initialize VehicleDetector: {e}")
            self.model = None

    def detect(self, frame) -> List[Tuple[List[float], float, int]]:
        """
        Perform raw detection on a frame.
        Returns: List of ([x1, y1, w, h], confidence, class_id)
        """
        if self.model is None:
            return []
            
        results = self.model(frame, conf=0.25, verbose=False)[0]
        
        detections = []
        for box in results.boxes:
            cls = int(box.cls[0].cpu().numpy())
            if cls in self.target_classes:
                # Convert xyxy to ltwh (left, top, width, height) for DeepSORT
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                w, h = x2 - x1, y2 - y1
                conf = float(box.conf[0].cpu().numpy())
                
                detections.append(([x1, y1, w, h], conf, cls))
                
        return detections

    def draw_detections(self, frame, detections):
        """Helper to draw detection results."""
        for ltwh, conf, cls in detections:
            x, y, w, h = map(int, ltwh)
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        return frame
