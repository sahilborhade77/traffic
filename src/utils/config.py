import yaml
import os

def load_config(config_path: str) -> dict:
    """
    Load configuration from a YAML file.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        
    return config

# Maintain backward compatibility for now
CONFIG = {}
for cfg_file in ['config.yaml', 'config/camera_config.yaml', 'config/traffic_config.yaml']:
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file, 'r', encoding='utf-8') as f:
                new_config = yaml.safe_load(f)
                if new_config:
                    CONFIG.update(new_config)
        except Exception as e:
            print(f"Warning: Could not load {cfg_file}: {e}")
