"""
Configuration loader and validator for traffic management system.

Supports:
- YAML configuration files with environment variable substitution
- Schema validation
- Configuration merging with defaults
- Runtime validation and type checking
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
import json
from enum import Enum


logger = logging.getLogger(__name__)


class ControlMode(str, Enum):
    """Signal control modes."""
    FIXED = "fixed"
    ADAPTIVE = "adaptive"
    MANUAL = "manual"


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class CameraConfig:
    """Camera configuration."""
    name: str
    url: str
    lane: str
    fps: int = 30
    resolution: tuple = (1280, 720)
    enabled: bool = True
    
    def validate(self) -> bool:
        """Validate camera configuration."""
        if not self.name or not self.url:
            raise ValueError("Camera name and URL are required")
        if self.fps <= 0 or self.fps > 120:
            raise ValueError(f"FPS must be between 1 and 120, got {self.fps}")
        if len(self.resolution) != 2:
            raise ValueError("Resolution must be (width, height)")
        return True


@dataclass
class ModelConfig:
    """Model configuration."""
    yolo_path: str
    detection_confidence: float = 0.5
    nms_threshold: float = 0.45
    device: str = "cuda"
    batch_size: int = 4
    
    def validate(self) -> bool:
        """Validate model configuration."""
        if not self.yolo_path:
            raise ValueError("YOLO model path is required")
        if not 0 < self.detection_confidence < 1:
            raise ValueError("Detection confidence must be between 0 and 1")
        if not 0 < self.nms_threshold < 1:
            raise ValueError("NMS threshold must be between 0 and 1")
        if self.batch_size <= 0:
            raise ValueError("Batch size must be positive")
        return True


@dataclass
class SignalConfig:
    """Signal timing configuration."""
    mode: ControlMode = ControlMode.ADAPTIVE
    cycle_length: int = 120
    min_green: int = 20
    max_green: int = 80
    yellow_duration: int = 5
    all_red_duration: int = 1
    
    def validate(self) -> bool:
        """Validate signal configuration."""
        if self.cycle_length <= 0:
            raise ValueError("Cycle length must be positive")
        if not 0 < self.min_green < self.max_green < self.cycle_length:
            raise ValueError("Green times invalid relative to cycle length")
        if self.yellow_duration <= 0:
            raise ValueError("Yellow duration must be positive")
        return True


@dataclass
class DatabaseConfig:
    """Database configuration."""
    type: str = "sqlite"  # sqlite or postgresql
    host: str = "localhost"
    port: int = 5432
    user: str = "traffic_user"
    password: str = "traffic_pass"
    database: str = "traffic_db"
    sqlite_path: str = "data/traffic.db"
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False
    
    def validate(self) -> bool:
        """Validate database configuration."""
        if self.type not in ["sqlite", "postgresql"]:
            raise ValueError("Database type must be 'sqlite' or 'postgresql'")
        if self.pool_size <= 0:
            raise ValueError("Pool size must be positive")
        return True
    
    def get_url(self) -> str:
        """Get database connection URL."""
        if self.type == "sqlite":
            return f"sqlite:///{self.sqlite_path}"
        else:
            return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class AnalyticsConfig:
    """Analytics and monitoring configuration."""
    enabled: bool = True
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    metrics_interval: int = 60  # seconds
    log_traffic_flow: bool = True
    
    def validate(self) -> bool:
        """Validate analytics configuration."""
        if self.prometheus_port <= 0 or self.prometheus_port > 65535:
            raise ValueError("Prometheus port must be between 1 and 65535")
        if self.metrics_interval <= 0:
            raise ValueError("Metrics interval must be positive")
        return True


@dataclass
class TrafficConfig:
    """Main traffic system configuration."""
    system_name: str = "Traffic Management System"
    log_level: LogLevel = LogLevel.INFO
    
    cameras: List[CameraConfig] = field(default_factory=list)
    model: ModelConfig = field(default_factory=ModelConfig)
    signal: SignalConfig = field(default_factory=SignalConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    analytics: AnalyticsConfig = field(default_factory=AnalyticsConfig)
    
    # General settings
    data_dir: str = "data"
    model_dir: str = "models"
    config_dir: str = "config"
    
    def validate(self) -> bool:
        """Validate entire configuration."""
        self.model.validate()
        self.signal.validate()
        self.database.validate()
        self.analytics.validate()
        
        for camera in self.cameras:
            camera.validate()
        
        if not self.cameras:
            logger.warning("No cameras configured")
        
        return True


class ConfigLoader:
    """Load and manage YAML configuration files."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader.
        
        Args:
            config_path: Path to YAML config file (default: env var CONFIG_PATH or config/traffic_config.yaml)
        """
        self.config_path = self._resolve_config_path(config_path)
        self.config: Optional[TrafficConfig] = None
    
    @staticmethod
    def _resolve_config_path(provided_path: Optional[str]) -> str:
        """Resolve configuration file path."""
        # Priority: provided path > env var > default
        if provided_path:
            return provided_path
        
        env_path = os.getenv("CONFIG_PATH")
        if env_path:
            return env_path
        
        return "config/traffic_config.yaml"
    
    def load(self) -> TrafficConfig:
        """Load configuration from YAML file with environment variable substitution."""
        config_file = Path(self.config_path)
        
        if not config_file.exists():
            logger.warning(f"Config file not found: {self.config_path}, using defaults")
            self.config = TrafficConfig()
        else:
            with open(config_file, 'r') as f:
                raw_config = yaml.safe_load(f)
            
            # Substitute environment variables
            raw_config = self._substitute_env_vars(raw_config)
            
            self.config = self._build_config(raw_config)
        
        # Validate configuration
        self.config.validate()
        logger.info(f"Configuration loaded from {self.config_path}")
        
        return self.config
    
    @staticmethod
    def _substitute_env_vars(config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively substitute environment variables in config values."""
        if isinstance(config_dict, dict):
            return {
                key: ConfigLoader._substitute_env_vars(value)
                for key, value in config_dict.items()
            }
        elif isinstance(config_dict, list):
            return [ConfigLoader._substitute_env_vars(item) for item in config_dict]
        elif isinstance(config_dict, str):
            # Substitute ${VAR_NAME} with environment variable value
            import re
            def replace_env(match):
                var_name = match.group(1)
                default_value = match.group(2) or ""
                return os.getenv(var_name, default_value)
            
            return re.sub(r'\$\{([A-Z_]+)(?::([^}]*))?\}', replace_env, config_dict)
        else:
            return config_dict
    
    @staticmethod
    def _build_config(raw_config: Dict[str, Any]) -> TrafficConfig:
        """Build TrafficConfig object from raw YAML dictionary."""
        config_data = {}
        
        # System level
        if 'system_name' in raw_config:
            config_data['system_name'] = raw_config['system_name']
        if 'log_level' in raw_config:
            config_data['log_level'] = LogLevel(raw_config['log_level'])
        
        # Directories
        for key in ['data_dir', 'model_dir', 'config_dir']:
            if key in raw_config:
                config_data[key] = raw_config[key]
        
        # Cameras
        if 'cameras' in raw_config:
            cameras = []
            for cam_data in raw_config['cameras']:
                cam_config = CameraConfig(
                    name=cam_data['name'],
                    url=cam_data['url'],
                    lane=cam_data['lane'],
                    fps=cam_data.get('fps', 30),
                    resolution=tuple(cam_data.get('resolution', [1280, 720])),
                    enabled=cam_data.get('enabled', True)
                )
                cameras.append(cam_config)
            config_data['cameras'] = cameras
        
        # Model
        if 'model' in raw_config:
            model_data = raw_config['model']
            config_data['model'] = ModelConfig(
                yolo_path=model_data['yolo_path'],
                detection_confidence=model_data.get('detection_confidence', 0.5),
                nms_threshold=model_data.get('nms_threshold', 0.45),
                device=model_data.get('device', 'cuda'),
                batch_size=model_data.get('batch_size', 4)
            )
        
        # Signal
        if 'signal' in raw_config:
            signal_data = raw_config['signal']
            config_data['signal'] = SignalConfig(
                mode=ControlMode(signal_data.get('mode', 'adaptive')),
                cycle_length=signal_data.get('cycle_length', 120),
                min_green=signal_data.get('min_green', 20),
                max_green=signal_data.get('max_green', 80),
                yellow_duration=signal_data.get('yellow_duration', 5),
                all_red_duration=signal_data.get('all_red_duration', 1)
            )
        
        # Database
        if 'database' in raw_config:
            db_data = raw_config['database']
            config_data['database'] = DatabaseConfig(
                type=db_data.get('type', 'sqlite'),
                host=db_data.get('host', 'localhost'),
                port=db_data.get('port', 5432),
                user=db_data.get('user', 'traffic_user'),
                password=db_data.get('password', 'traffic_pass'),
                database=db_data.get('database', 'traffic_db'),
                sqlite_path=db_data.get('sqlite_path', 'data/traffic.db'),
                pool_size=db_data.get('pool_size', 10),
                max_overflow=db_data.get('max_overflow', 20),
                echo=db_data.get('echo', False)
            )
        
        # Analytics
        if 'analytics' in raw_config:
            analytics_data = raw_config['analytics']
            config_data['analytics'] = AnalyticsConfig(
                enabled=analytics_data.get('enabled', True),
                prometheus_enabled=analytics_data.get('prometheus_enabled', True),
                prometheus_port=analytics_data.get('prometheus_port', 9090),
                metrics_interval=analytics_data.get('metrics_interval', 60),
                log_traffic_flow=analytics_data.get('log_traffic_flow', True)
            )
        
        return TrafficConfig(**config_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        if not self.config:
            return {}
        
        config_dict = asdict(self.config)
        
        # Convert nested dataclasses
        if 'cameras' in config_dict:
            config_dict['cameras'] = [asdict(cam) for cam in self.config.cameras]
        if 'model' in config_dict:
            config_dict['model'] = asdict(self.config.model)
        if 'signal' in config_dict:
            config_dict['signal'] = asdict(self.config.signal)
            config_dict['signal']['mode'] = self.config.signal.mode.value
        if 'database' in config_dict:
            config_dict['database'] = asdict(self.config.database)
        if 'analytics' in config_dict:
            config_dict['analytics'] = asdict(self.config.analytics)
        
        # Convert enums
        config_dict['log_level'] = self.config.log_level.value
        
        return config_dict
    
    def save(self, output_path: Optional[str] = None) -> None:
        """Save configuration to YAML file."""
        if not self.config:
            raise RuntimeError("No configuration loaded")
        
        output_file = Path(output_path or self.config_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        config_dict = self.to_dict()
        
        with open(output_file, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Configuration saved to {output_file}")


# Global configuration instance
_global_config: Optional[TrafficConfig] = None


def get_config(reload: bool = False) -> TrafficConfig:
    """Get global configuration instance."""
    global _global_config
    
    if _global_config is None or reload:
        loader = ConfigLoader()
        _global_config = loader.load()
    
    return _global_config


def load_config(config_path: Optional[str] = None) -> TrafficConfig:
    """Load configuration from file."""
    loader = ConfigLoader(config_path)
    return loader.load()
