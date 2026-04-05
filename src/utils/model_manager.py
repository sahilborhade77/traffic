"""
Shared GPU Model Manager — 4GB VRAM Optimization
-------------------------------------------------
Loads ONE YOLOv8n model and ONE EasyOCR reader into VRAM.
All detection modules share this singleton — eliminates redundant GPU allocations.
"""

import torch
import logging
from ultralytics import YOLO
import easyocr

logger = logging.getLogger(__name__)

class ModelManager:
    """
    Singleton GPU Model Manager.
    All detectors share one YOLO model and one OCR reader.
    YOLO class filtering handles task-switching (vehicles, helmets, phones, persons).
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def initialize(self, yolo_model_path: str = 'yolov8n.pt', use_gpu: bool = True):
        if self._initialized:
            return
        
        self.device = 'cuda' if (use_gpu and torch.cuda.is_available()) else 'cpu'
        logger.info(f"ModelManager: GPU={self.device}, VRAM Budget=4GB")

        # ── Single YOLO model handles ALL detection tasks ──
        logger.info("Loading shared YOLOv8n model...")
        self.yolo = YOLO(yolo_model_path)
        self.yolo.to(self.device)
        if self.device == 'cuda':
            self.yolo.model.half()  # FP16 → saves ~1GB VRAM
        logger.info("YOLOv8n loaded in FP16.")

        # ── Single EasyOCR instance ──
        logger.info("Loading EasyOCR (en)...")
        self.ocr = easyocr.Reader(['en'], gpu=(self.device == 'cuda'))
        logger.info("EasyOCR loaded.")

        # COCO class reference
        self.CLASS_NAMES = self.yolo.names  # {0: 'person', 2: 'car', ...}

        self._initialized = True
        self._log_vram()

    def detect(self, frame, conf: float = 0.35, classes: list = None):
        """
        Run YOLO inference. Filter by class IDs if provided.
        classes: e.g. [0] for persons only, [2,3,5,7] for vehicles
        """
        if not self._initialized:
            raise RuntimeError("ModelManager not initialized. Call .initialize() first.")
        kwargs = {'conf': conf, 'verbose': False}
        if classes:
            kwargs['classes'] = classes
        return self.yolo(frame, **kwargs)[0]

    def _log_vram(self):
        if self.device == 'cuda':
            allocated = torch.cuda.memory_allocated() / 1e9
            reserved = torch.cuda.memory_reserved() / 1e9
            logger.info(f"VRAM: Allocated={allocated:.2f}GB | Reserved={reserved:.2f}GB")

    def free_cache(self):
        if self.device == 'cuda':
            torch.cuda.empty_cache()

# Global singleton
model_manager = ModelManager()
