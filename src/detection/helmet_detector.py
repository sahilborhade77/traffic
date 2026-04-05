from ultralytics import YOLO
import torch
import logging

logger = logging.getLogger(__name__)

class HelmetDetector:
    """
    Helmet Detection for Motorcyclists using YOLOv8.
    """
    def __init__(self, model_path='helmet_model.pt'):
        """
        Initialize the helmet detector.
        """
        try:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.model = YOLO(model_path)
            logger.info(f"Helmet Detector initialized on {self.device}")
        except Exception as e:
            logger.error(f"Failed to initialize Helmet Detector: {e}")
            self.model = None

    def detect(self, motorcyclist_crop):
        """
        Detect helmet usage in motorcyclist crop.
        """
        if self.model is None:
            return None
        
        results = self.model(motorcyclist_crop, conf=0.5, verbose=False)[0]
        # In this model, 0: NO-HELMET, 1: HELMET
        detections = []
        for box in results.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            detections.append({
                'label': results.names[cls],
                'confidence': conf,
                'bbox': box.xyxy[0].cpu().numpy().astype(int)
            })
            
        return detections
