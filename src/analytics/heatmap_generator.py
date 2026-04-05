"""
Feature 4: Heatmap Analytics Dashboard
----------------------------------------
Generates real-time traffic density heatmaps from vehicle trajectory data.
Runs entirely on CPU using OpenCV — zero VRAM cost.
"""

import cv2
import numpy as np
import logging
from typing import Dict, List, Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class HeatmapGenerator:
    """
    Accumulates vehicle centroid positions and renders a live congestion heatmap.
    Color gradient: Blue (low) → Green (medium) → Red (high density).
    CPU-based (numpy + OpenCV). VRAM cost: 0.
    """
    def __init__(self, frame_shape: Tuple[int, int], decay_factor: float = 0.98):
        """
        Args:
            frame_shape:   (height, width) of the video frame
            decay_factor:  How fast old positions fade (0.98 = slow fade)
        """
        h, w = frame_shape
        self.heatmap = np.zeros((h, w), dtype=np.float32)
        self.decay = decay_factor
        self.frame_shape = frame_shape
        logger.info(f"HeatmapGenerator initialized for frame {w}x{h}")

    def update(self, tracks: Dict) -> None:
        """
        Update heatmap with current vehicle centroids.
        
        Args:
            tracks: Dict[track_id, VehicleTrack] from DeepSORTTracker
        """
        # Decay existing heat (simulates time passing)
        self.heatmap *= self.decay

        for track in tracks.values():
            cx, cy = track.get_centroid()
            cx, cy = int(cx), int(cy)
            h, w = self.frame_shape

            if 0 < cx < w and 0 < cy < h:
                # Apply a Gaussian blob at vehicle position
                sigma = 30
                x_range = slice(max(0, cx - sigma*2), min(w, cx + sigma*2))
                y_range = slice(max(0, cy - sigma*2), min(h, cy + sigma*2))

                # Create local Gaussian patch
                patch_h = y_range.stop - y_range.start
                patch_w = x_range.stop - x_range.start
                if patch_h > 0 and patch_w > 0:
                    yy, xx = np.mgrid[-sigma*2:sigma*2:patch_h*1j, -sigma*2:sigma*2:patch_w*1j]
                    gaussian = np.exp(-(xx**2 + yy**2) / (2*sigma**2)).astype(np.float32)
                    self.heatmap[y_range, x_range] += gaussian

    def render(self, frame: np.ndarray, alpha: float = 0.5) -> np.ndarray:
        """
        Overlay heatmap on camera frame.
        
        Args:
            frame: Original BGR frame
            alpha: Blending transparency (0=heatmap only, 1=frame only)
        Returns:
            Frame with colored heatmap overlay
        """
        # Normalize to 0-255
        hm_norm = cv2.normalize(self.heatmap, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        # Apply color map: COLORMAP_JET (Blue→Green→Red)
        hm_color = cv2.applyColorMap(hm_norm, cv2.COLORMAP_JET)

        # Blend with original frame
        blended = cv2.addWeighted(frame, 1 - alpha, hm_color, alpha, 0)

        # Add timestamp label
        cv2.putText(blended, f"Traffic Density Heatmap | {datetime.now().strftime('%H:%M:%S')}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return blended

    def save_snapshot(self, frame: np.ndarray, output_dir: str = 'output/heatmaps') -> str:
        """Save heatmap snapshot to disk."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = str(Path(output_dir) / f"heatmap_{timestamp}.jpg")
        rendered = self.render(frame)
        cv2.imwrite(filepath, rendered)
        logger.info(f"Heatmap saved: {filepath}")
        return filepath

    def reset(self):
        """Clear accumulated heat data."""
        self.heatmap[:] = 0
