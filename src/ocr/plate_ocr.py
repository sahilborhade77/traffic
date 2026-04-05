import cv2
import numpy as np
import easyocr
import re
import logging
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PlateResult:
    """Result of license plate OCR."""
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]
    cleaned_text: str
    is_valid: bool

class IndianPlateOCR:
    """
    Advanced License Plate OCR for Indian vehicle formats.
    Using EasyOCR with specialized preprocessing and correction.
    """
    def __init__(self, use_gpu: bool = True):
        """
        Initialize EasyOCR for Indian license plates.
        """
        try:
            self.reader = easyocr.Reader(['en'], gpu=use_gpu)
            logger.info(f"IndianPlateOCR initialized (GPU: {use_gpu})")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            self.reader = None
        
        # Indian plate patterns
        # Standard: MH12AB1234
        # BH Series: MH12BH1234
        self.patterns = [
            r'^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$',  # Standard format
            r'^[A-Z]{2}\d{2}[A-Z]{3}\d{4}$',     # New BH series
        ]
    
    def preprocess_plate_image(self, plate_img: np.ndarray) -> np.ndarray:
        """
        Preprocess plate image for better OCR accuracy.
        """
        if plate_img is None or plate_img.size == 0:
            return None
            
        # Convert to grayscale
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        
        # Increase contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(enhanced)
        
        # Adaptive thresholding
        binary = cv2.adaptiveThreshold(
            denoised, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Resize for better OCR (height = 60px works well)
        h, w = binary.shape
        new_h = 60
        new_w = int(w * (new_h / h))
        resized = cv2.resize(binary, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        
        return resized
    
    def clean_plate_text(self, text: str) -> str:
        """
        Clean OCR output to match Indian plate format.
        """
        # Remove spaces and special characters
        cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
        
        # Common OCR mistakes
        replacements = {
            'O': '0', 'I': '1', 'Z': '2', 'S': '5',
            'B': '8', 'G': '6', 'Q': '0'
        }
        
        # Apply corrections intelligently
        # First 2 chars should be letters (state code)
        if len(cleaned) >= 2:
            state_code = list(cleaned[:2])
            for i in range(2):
                if state_code[i].isdigit():
                    # Likely a letter misread as digit
                    for letter, digit in replacements.items():
                        if digit == state_code[i]:
                            state_code[i] = letter
                            break
            cleaned = "".join(state_code) + cleaned[2:]
        
        # Characters 3-4 should be digits
        if len(cleaned) >= 4:
            district_code = list(cleaned[2:4])
            for i in range(2): # indices 0-1 within district_code substring
                if district_code[i].isalpha():
                    for letter, digit in replacements.items():
                        if letter == district_code[i]:
                            district_code[i] = digit
                            break
            cleaned = cleaned[:2] + "".join(district_code) + cleaned[4:]
        
        return cleaned
    
    def validate_indian_plate(self, text: str) -> bool:
        """
        Validate if text matches Indian plate pattern.
        """
        for pattern in self.patterns:
            if re.match(pattern, text):
                return True
        return False
    
    def read_plate(self, plate_img: np.ndarray) -> Optional[PlateResult]:
        """
        Main method to read license plate.
        """
        if self.reader is None or plate_img is None:
            return None
            
        # Preprocess
        preprocessed = self.preprocess_plate_image(plate_img)
        if preprocessed is None:
            return None
            
        # Perform OCR
        results = self.reader.readtext(preprocessed, detail=1)
        
        if not results:
            return None
        
        # Get result with highest confidence
        best_result = max(results, key=lambda x: x[2])
        bbox, text, confidence = best_result
        
        # Clean text
        cleaned = self.clean_plate_text(text)
        
        # Validate
        is_valid = self.validate_indian_plate(cleaned)
        
        # Convert bbox to x, y, w, h
        bbox_array = np.array(bbox)
        x_min = int(bbox_array[:, 0].min())
        y_min = int(bbox_array[:, 1].min())
        x_max = int(bbox_array[:, 0].max())
        y_max = int(bbox_array[:, 1].max())
        
        return PlateResult(
            text=text,
            confidence=confidence,
            bbox=(x_min, y_min, x_max - x_min, y_max - y_min),
            cleaned_text=cleaned,
            is_valid=is_valid
        )

# usage example
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ocr = IndianPlateOCR(use_gpu=True)
    
    # Example logic (would need a real image to run)
    # plate_img = cv2.imread("data/samples/plate.jpg")
    # result = ocr.read_plate(plate_img)
    # print(result)
