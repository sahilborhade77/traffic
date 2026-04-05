import cv2
import logging
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, Any

logger = logging.getLogger(__name__)

class EvidenceManager:
    """
    Manages collection of violation snapshots, annotations, and structured metadata.
    Ensures all legal evidence is securely stored.
    """
    def __init__(self, output_dir: str = 'output/evidence'):
        """
        Initialize evidence manager with a base directory.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Subdirectories
        self.snapshots_dir = self.output_dir / "snapshots"
        self.metadata_dir = self.output_dir / "metadata"
        self.passages_dir = self.output_dir / "passages"
        
        for d in [self.snapshots_dir, self.metadata_dir, self.passages_dir]:
            d.mkdir(exist_ok=True)
            
        logger.info(f"Evidence Manager initialized. Storage: {output_dir}")

    def capture_violation_evidence(self, frame, bbox, violation_type, metadata: Dict[str, Any]) -> Dict[str, str]:
        """
        Formal method to capture complete violation evidence.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        track_id = metadata.get('track_id', 'unknown')
        filename_base = f"{violation_type}_{track_id}_{timestamp}"
        
        # Save Snapshot
        image_path = self.snapshots_dir / f"{filename_base}.jpg"
        cv2.imwrite(str(image_path), frame)
        
        # Save Crop (Enhanced Evidence)
        if bbox:
            x, y, w, h = map(int, bbox)
            crop = frame[y:y+h, x:x+w]
            crop_path = self.snapshots_dir / f"{filename_base}_crop.jpg"
            cv2.imwrite(str(crop_path), crop)
        
        # Save Metadata
        meta_path = self.metadata_dir / f"{filename_base}.json"
        with open(meta_path, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'violation_type': violation_type,
                'metadata': metadata,
                'image_path': str(image_path)
            }, f, indent=4)
            
        return {
            'image_path': str(image_path),
            'metadata_path': str(meta_path)
        }

    def capture_screenshot(self, frame, label: str):
        """Simple helper for generic captures."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{label}_{timestamp}.jpg"
        filepath = self.snapshots_dir / filename
        cv2.imwrite(str(filepath), frame)
        return str(filepath)
