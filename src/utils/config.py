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
if os.path.exists('config/camera_config.yaml'):
    try:
        with open('config/camera_config.yaml', 'r') as f:
            CONFIG = yaml.safe_load(f)
    except:
        pass
