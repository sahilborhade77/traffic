import logging
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional

from src.ocr.plate_ocr import IndianPlateOCR
from src.evidence.evidence_manager import EvidenceManager
from src.notification.echallan_pdf import EChallanPDFGenerator
from src.violations.repeat_offender import RepeatOffenderEngine
from src.database.violation_db import ViolationDatabase

logger = logging.getLogger(__name__)

class ViolationProcessor:
    """
    Centralized processor for handling detected traffic violations.
    Orchestrates OCR, evidence collection, database logging, and challan generation.
    """
    def __init__(self, db_url: str = 'sqlite:///traffic.db', output_dir: str = 'output'):
        self.ocr = IndianPlateOCR(use_gpu=False) # Default to False for stability
        self.evidence_manager = EvidenceManager(output_dir=f'{output_dir}/evidence')
        self.pdf_generator = EChallanPDFGenerator(output_dir=f'{output_dir}/challans')
        self.repeat_offender_engine = RepeatOffenderEngine()
        self.db = ViolationDatabase(db_url=db_url)
        
        logger.info("ViolationProcessor initialized and ready.")

    def process_violation(self, 
                          frame: np.ndarray, 
                          violation_data: Dict[str, Any], 
                          plate_crop: Optional[np.ndarray] = None) -> Optional[Dict[str, Any]]:
        """
        Processes a raw violation into a formal record with evidence.
        
        Args:
            frame: Full frame from camera
            violation_data: Metadata about the violation (type, track_id, bbox, etc.)
            plate_crop: Cropped image of the license plate (optional)
            
        Returns:
            Dict containing processing results and paths to generated artifacts.
        """
        track_id = violation_data.get('track_id', 'unknown')
        v_type = violation_data.get('violation_type', 'UNKNOWN')
        
        logger.info(f"Processing {v_type} violation for Track {track_id}")
        
        # 1. OCR - Extract License Plate
        plate_number = "UNKNOWN"
        ocr_confidence = 0.0
        
        if plate_crop is not None:
            ocr_result = self.ocr.read_plate(plate_crop)
            if ocr_result and ocr_result.is_valid:
                plate_number = ocr_result.cleaned_text
                ocr_confidence = ocr_result.confidence
                logger.info(f"OCR Success: {plate_number} (Conf: {ocr_confidence:.2f})")
        
        # 2. Evidence Capture
        evidence = self.evidence_manager.capture_violation_evidence(
            frame, 
            violation_data.get('bbox'), 
            v_type, 
            {**violation_data, 'plate_number': plate_number}
        )
        
        # 3. Repeat Offender Check
        is_repeat = self.repeat_offender_engine.check(plate_number)
        
        # 4. Database Logging
        # Map fine amount (placeholder or from violation_types)
        from src.violations.violation_types import ViolationType, get_fine_amount
        try:
            enum_type = ViolationType[v_type]
            fine_amount = get_fine_amount(enum_type)
        except (KeyError, ValueError):
            fine_amount = 500 # Default fine
            
        violation_id = self.db.log_violation({
            'plate_number': plate_number,
            'violation_type': v_type,
            'fine_amount': fine_amount,
            'image_path': evidence['image_path'],
            'timestamp': datetime.now()
        })
        
        # 5. E-Challan PDF Generation
        challan_path = self.pdf_generator.generate(
            violation_id=violation_id or 0,
            plate_number=plate_number,
            owner_name="Vehicle Owner", # Placeholder
            owner_phone="+91-XXXXXXXXXX", # Placeholder
            violation_type=v_type,
            violation_location="Intersection A", # Placeholder
            violation_timestamp=datetime.now(),
            camera_id="CAM_01", # Placeholder
            fine_amount=fine_amount,
            evidence_image_path=evidence['image_path']
        )
        
        result = {
            'violation_id': violation_id,
            'plate_number': plate_number,
            'is_repeat_offender': is_repeat,
            'evidence_paths': evidence,
            'challan_path': challan_path,
            'fine_amount': fine_amount
        }
        
        logger.info(f"Violation Processed: {v_type} | ID: {violation_id} | Path: {challan_path}")
        return result

if __name__ == "__main__":
    # Minimal test
    logging.basicConfig(level=logging.INFO)
    proc = ViolationProcessor()
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    dummy_violation = {
        'track_id': 99,
        'violation_type': 'RED_LIGHT',
        'bbox': [100, 100, 50, 50]
    }
    # No OCR test (no plate crop)
    res = proc.process_violation(dummy_frame, dummy_violation)
    print(f"Processor Result: {res}")
