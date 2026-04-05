"""
Feature 8: Night Vision / Low Light Enhancement
-------------------------------------------------
Applies CLAHE + brightness normalization before YOLO inference.
Significantly improves detection accuracy in low-light conditions.
CPU-only via OpenCV. VRAM cost: 0.
"""

import cv2
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class NightVisionEnhancer:
    """
    Enhances low-light video frames before detection to improve accuracy at night.
    
    Pipeline:
        1. Convert to LAB color space
        2. Apply CLAHE to L (lightness) channel
        3. Merge and convert back to BGR
        4. Gamma correction for perceptual brightness
    CPU-only — zero VRAM impact.
    """
    def __init__(self, clip_limit: float = 2.5, tile_size: int = 8, gamma: float = 1.2):
        """
        Args:
            clip_limit: CLAHE contrast boost (higher = more contrast)
            tile_size:  CLAHE grid tile size
            gamma:      Gamma correction factor (>1 = brighter)
        """
        self.clahe = cv2.createCLAHE(
            clipLimit=clip_limit,
            tileGridSize=(tile_size, tile_size)
        )
        self.gamma = gamma
        self._gamma_table = self._build_gamma_table(gamma)
        logger.info(f"NightVisionEnhancer ready. CLAHE clip={clip_limit}, gamma={gamma}")

    def _build_gamma_table(self, gamma: float) -> np.ndarray:
        """Precompute gamma correction LUT for fast per-pixel adjustment."""
        inv_gamma = 1.0 / gamma
        table = np.array([
            ((i / 255.0) ** inv_gamma) * 255
            for i in range(256)
        ]).astype(np.uint8)
        return table

    def is_low_light(self, frame: np.ndarray, threshold: float = 80.0) -> bool:
        """
        Auto-detect whether a frame is low-light.
        
        Args:
            threshold: Mean brightness below which enhancement is applied
        Returns:
            True if frame is dark enough to need enhancement
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray)) < threshold

    def enhance(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply CLAHE + gamma correction to the frame.
        Safe to call on any frame regardless of lighting.
        """
        if frame is None or frame.size == 0:
            return frame

        # Step 1: Convert BGR → LAB
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Step 2: CLAHE on L channel (lightness only, no color distortion)
        l_enhanced = self.clahe.apply(l)

        # Step 3: Merge back and convert to BGR
        lab_enhanced = cv2.merge([l_enhanced, a, b])
        enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

        # Step 4: Gamma correction
        enhanced = cv2.LUT(enhanced, self._gamma_table)

        return enhanced

    def smart_enhance(self, frame: np.ndarray, threshold: float = 80.0) -> tuple:
        """
        Only enhance if frame is detected as low-light.
        Returns (enhanced_frame, was_enhanced: bool).
        """
        if self.is_low_light(frame, threshold):
            return self.enhance(frame), True
        return frame, False
