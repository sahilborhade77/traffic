from ultralytics import YOLO
import cv2
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VehicleDetector:
    """
    Vehicle Detection and Tracking using YOLOv8.
    """
    def __init__(self, model_path='yolov8n.pt', tracker='botsort.yaml'):
        """
        Initialize the detector with a pre-trained YOLO model and tracker configuration.
        :param model_path: Path to the YOLO model weights
        :param tracker: Tracker type ('botsort.yaml' or 'bytetrack.yaml')
        """
        try:
            self.model = YOLO(model_path)
            self.tracker = tracker
            self.target_classes = [2, 3, 5, 7] # car, motorcycle, bus, truck
            logger.info(f"Model {model_path} with tracker {tracker} initialized.")
        except Exception as e:
            logger.error(f"Error initializing detector: {e}")
            raise

    def track(self, frame, conf_threshold=0.3):
        """
        Track vehicles across frames.
        :param frame: current video frame
        :param conf_threshold: confidence for tracker
        :return: List of tracked objects with IDs
        """
        results = self.model.track(frame, persist=True, conf=conf_threshold, tracker=self.tracker, verbose=False)[0]
        
        detections = []
        if results.boxes.id is not None:
            boxes = results.boxes.xyxy.cpu().numpy().astype(int)
            ids = results.boxes.id.cpu().numpy().astype(int)
            classes = results.boxes.cls.cpu().numpy().astype(int)
            confs = results.boxes.conf.cpu().numpy()
            
            for box, track_id, cls, conf in zip(boxes, ids, classes, confs):
                if cls in self.target_classes:
                    x1, y1, x2, y2 = box
                    label = results.names[cls]
                    
                    # Calculate centroid for tracking/counting
                    cx = int((x1 + x2) / 2)
                    cy = int((y1 + y2) / 2)
                    
                    detections.append({
                        'track_id': int(track_id),
                        'class_id': int(cls),
                        'label': label,
                        'confidence': float(conf),
                        'bbox': (x1, y1, x2, y2),
                        'centroid': (cx, cy)
                    })
        
        return detections

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
