from ultralytics import YOLO
import cv2
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VehicleDetector:
    """
    Vehicle Detection using YOLOv8.
    """
    def __init__(self, model_path='yolov8n.pt'):
        """
        Initialize the detector with a pre-trained YOLO model.
        :param model_path: Path to the YOLO model weights (default: yolov8n.pt)
        """
        try:
            self.model = YOLO(model_path)
            # Define common traffic-related classes in YOLOv8 (COCO dataset)
            # 2: car, 3: motorcycle, 5: bus, 7: truck
            self.target_classes = [2, 3, 5, 7] 
            logger.info(f"Model loaded successfully from {model_path}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise

    def detect(self, frame, conf_threshold=0.5):
        """
        Detect vehicles in a frame.
        :param frame: OpenCV image/frame
        :param conf_threshold: Confidence threshold for detections
        :return: Detection results (boxes, confidences, class_ids)
        """
        results = self.model(frame, conf=conf_threshold, verbose=False)[0]
        
        detections = []
        for box in results.boxes:
            class_id = int(box.cls[0])
            if class_id in self.target_classes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                label = results.names[class_id]
                detections.append({
                    'class_id': class_id,
                    'label': label,
                    'confidence': conf,
                    'bbox': (x1, y1, x2, y2)
                })
        
        return detections

    def draw_detections(self, frame, detections):
        """
        Draw bounding boxes and labels on the frame.
        :param frame: OpenCV image/frame
        :param detections: List of detections from self.detect()
        :return: Frame with annotations
        """
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            label = f"{det['label']} {det['confidence']:.2f}"
            
            # Draw box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            # Draw label background
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - 20), (x1 + w, y1), (0, 255, 0), -1)
            # Draw text
            cv2.putText(frame, label, (x1, y1 - 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            
        return frame
