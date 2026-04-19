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
        try:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.model = YOLO(model_path).to(self.device)
            # self.model.half() # Disabled for compatibility; using FP32
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

    def track(self, frame) -> List[dict]:
        """
        Perform detection and tracking on a frame.
        Returns: List of detection dictionaries with 'label', 'bbox', 'conf', 'track_id'
        """
        if self.model is None:
            return []
            
        # Use YOLOv8's built-in tracker (BoTSORT or ByteTrack)
        results = self.model.track(frame, persist=True, conf=0.25, verbose=False)[0]
        
        detections = []
        if results.boxes is not None and results.boxes.id is not None:
            # Class mapping (COCO)
            class_map = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}
            
            for box, track_id in zip(results.boxes, results.boxes.id):
                cls_id = int(box.cls[0].cpu().numpy())
                if cls_id in self.target_classes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0].cpu().numpy())
                    
                    detections.append({
                        'label': class_map.get(cls_id, 'vehicle'),
                        'bbox': [x1, y1, x2, y2],
                        'conf': conf,
                        'track_id': int(track_id.cpu().numpy())
                    })
                    
        return detections

    def draw_detections(self, frame, detections):
        """Helper to draw detection results."""
        for det in detections:
            x1, y1, x2, y2 = map(int, det['bbox'])
            label = f"{det['label']} {det['track_id']} {det['conf']:.2f}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        return frame
