import yaml
import os
import logging
import numpy as np

logger = logging.getLogger(__name__)

class CameraConfigManager:
    """
    Unified config loader for industrial scaling.
    """
    def __init__(self, config_path='config/camera_config.yaml'):
        self.config_path = config_path
        self.configs = self._load_all_configs()

    def _load_all_configs(self):
        """Load YAML file from the configs directory."""
        if not os.path.exists(self.config_path):
            logger.error(f"Config file {self.config_path} not found!")
            return {}
            
        with open(self.config_path, 'r') as f:
            try:
                return yaml.safe_load(f)
            except yaml.YAMLError as exc:
                logger.error(f"Error parsing YAML: {exc}")
                return {}

    def get_camera_context(self, camera_id):
        """
        Automatically return calibrated points and ROIs for a specific camera.
        """
        if camera_id not in self.configs:
            logger.warning(f"Unknown Camera ID: {camera_id}. Falling back to default.")
            return {
                'points': [],
                'roi': {},
                'conf': 0.45,
                'aug': False
            }
            
        cfg = self.configs[camera_id]
        
        processed_roi = {}
        for name, pts in cfg.get('roi_zones', {}).items():
            processed_roi[name] = np.array(pts, np.int32)
            
        return {
            'perspective_points': np.float32(cfg.get('perspective_points', [])),
            'roi_zones': processed_roi,
            'confidence': cfg.get('min_confidence', 0.45),
            'augmentation': cfg.get('use_augmentation', True)
        }
