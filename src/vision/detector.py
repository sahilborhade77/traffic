from ultralytics import YOLO
import cv2
import torch
import os
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VehicleDetector:
    """
    Vehicle Detection and Tracking using YOLOv8.
    """
    def __init__(self, model_path='yolov8s.pt', tracker='botsort.yaml'):
        """
        Initialize the detector with GPU support and optimized model format.
        """
        try:
            # Check for GPU (CUDA) availability and initialize device
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            logger.info(f"YOLOv8 Hardware Acceleration: {self.device.upper()}")
            
            # Use TensorRT (.engine) if available on GPU for maximum speed
            if model_path.endswith('.pt') and self.device == 'cuda':
                engine_path = model_path.replace('.pt', '.engine')
                if os.path.exists(engine_path):
                    model_path = engine_path
                    logger.info(f"Loading optimized TensorRT model: {model_path}")
            
            self.model = YOLO(model_path)
            self.tracker = tracker
            self.target_classes = [2, 3, 5, 7] # car, motorcycle, bus, truck
            logger.info(f"YOLOv8 Model '{model_path}' successfully loaded on {self.device}.")
        except Exception as e:
            logger.critical(f"CRITICAL: Failed to initialize YOLOv8 Detector: {e}")
            raise RuntimeError(f"Detector initialization failed: {e}")

    def track(self, frame, conf_threshold=0.2):
        """
        Track vehicles across frames. Improved with Multi-Scale & Agnostic NMS.
        """
        try:
            # imgsz=640 is standard, agnostic_nms=True handles overlapping bboxes
            results = self.model.track(
                frame, 
                persist=True, 
                conf=conf_threshold, 
                iou=0.45,
                tracker=self.tracker, 
                verbose=False, 
                imgsz=640,
                agnostic_nms=True,
                device=self.device
            )[0]
            
            detections = []
            if results.boxes is not None:
                # Ensure boxes and attributes are moved to CPU for processing
                boxes = results.boxes.xyxy.cpu().numpy().astype(int)
                classes = results.boxes.cls.cpu().numpy().astype(int)
                confs = results.boxes.conf.cpu().numpy()
                
                # Check if IDs exist (tracker might still be warm-up)
                ids = results.boxes.id.cpu().numpy().astype(int) if results.boxes.id is not None else [0] * len(boxes)
                
                for box, track_id, cls, conf in zip(boxes, ids, classes, confs):
                    if cls in self.target_classes:
                        x1, y1, x2, y2 = box
                        label = results.names[cls]
                        cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
                        
                        detections.append({
                            'track_id': int(track_id),
                            'class_id': int(cls),
                            'label': label,
                            'confidence': float(conf),
                            'bbox': (x1, y1, x2, y2),
                            'centroid': (cx, cy)
                        })
            
            return detections
        except Exception as e:
            logger.error(f"Error during frame tracking: {e}")
            return []

    def draw_detections(self, frame, detections, draw_id=True):
        """
        Draw bounding boxes, stable IDs, and labels.
        """
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            label = f"{det['label']} {det['track_id']}" if draw_id else det['label']
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.circle(frame, det['centroid'], 4, (0, 0, 255), -1)
            
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - 20), (x1 + w, y1), (0, 255, 0), -1)
            cv2.putText(frame, label, (x1, y1 - 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            
        return frame
