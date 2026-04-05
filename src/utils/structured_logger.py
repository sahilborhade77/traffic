"""
Structured Logging System with Loguru

Provides comprehensive logging with structured JSON output, log rotation,
performance monitoring, and debugging support across the traffic system.

Features:
- Loguru integration with automatic rotation
- JSON structured logging for analytics
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- File and console output with different formats
- Performance metric logging
- Request/response tracking
- Error tracking with context
- Configurable log retention

Author: Traffic Intelligence Team
Version: 1.0.0
"""

import sys
import json
import time
import logging
import functools
from pathlib import Path
from typing import Optional, Callable, Any, Dict
from datetime import datetime
from dataclasses import dataclass, asdict
from functools import wraps

try:
    from loguru import logger as loguru_logger
    LOGURU_AVAILABLE = True
except ImportError:
    LOGURU_AVAILABLE = False
    loguru_logger = None  # type: ignore

# Standard logging as fallback
logger = logging.getLogger(__name__)


@dataclass
class LogEvent:
    """Structured log event."""
    timestamp: str
    level: str
    message: str
    module: str
    function: str
    line: int
    context: Dict[str, Any] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class PerformanceMetric:
    """Performance measurement."""
    name: str
    duration_ms: float
    timestamp: str = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'duration_ms': f"{self.duration_ms:.2f}",
            'timestamp': self.timestamp,
            'metadata': self.metadata
        }


class StructuredLogger:
    """
    High-level structured logging interface with performance tracking.
    
    Features:
    - Automatic JSON logging
    - Performance metric tracking
    - Request/response logging
    - Error context tracking
    - Log rotation and retention
    
    Example:
        ```python
        slogger = StructuredLogger('traffic_vision')
        
        # Info logging
        slogger.info("Vehicle detected", {
            'track_id': 123,
            'class': 'car',
            'confidence': 0.95
        })
        
        # Performance tracking
        with slogger.timer('frame_processing'):
            process_frame(frame)
        
        # Error logging
        try:
            connect_to_camera()
        except Exception as e:
            slogger.error("Camera connection failed", {
                'error': str(e),
                'host': camera_host
            })
        
        # Request tracking
        slogger.log_request('GET', '/api/traffic/status', 200, 45.2)
        ```
    """
    
    def __init__(
        self,
        name: str,
        log_dir: str = "logs",
        log_level: str = "INFO",
        json_format: bool = True,
        enable_file_logging: bool = True,
        enable_console_logging: bool = True,
        max_bytes: int = 10485760,  # 10MB
        backup_count: int = 5
    ):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name
            log_dir: Directory for log files
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            json_format: Enable JSON structured logging
            enable_file_logging: Write logs to files
            enable_console_logging: Write logs to console
            max_bytes: Max size of log file before rotation
            backup_count: Number of backup files to keep
        """
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_level = log_level
        self.json_format = json_format
        self.enable_file_logging = enable_file_logging
        self.enable_console_logging = enable_console_logging
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        
        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup loguru if available
        self.using_loguru = LOGURU_AVAILABLE and loguru_logger is not None
        self.logger = None
        
        if self.using_loguru:
            self._setup_loguru()
        else:
            self._setup_fallback()
        
        logger.info(f"StructuredLogger '{name}' initialized (using_loguru={self.using_loguru})")
    
    def _setup_loguru(self) -> None:
        """Setup loguru logger."""
        import loguru
        
        # Remove default handler
        loguru_logger.remove()
        
        # Console handler
        if self.enable_console_logging:
            loguru_logger.add(
                sys.stderr,
                level=self.log_level,
                format=(
                    "<level>{level: <8}</level> | "
                    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                    "<level>{message}</level>"
                )
            )
        
        # File handler with rotation
        if self.enable_file_logging:
            log_file = self.log_dir / f"{self.name}.log"
            loguru_logger.add(
                str(log_file),
                level=self.log_level,
                format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name} | {message}",
                rotation=f"{self.max_bytes} B",
                retention=self.backup_count
            )
            
            # JSON log file
            if self.json_format:
                json_log_file = self.log_dir / f"{self.name}.json"
                loguru_logger.add(
                    str(json_log_file),
                    level=self.log_level,
                    format=self._json_format,
                    rotation=f"{self.max_bytes} B",
                    retention=self.backup_count,
                    serialize=True
                )
        
        self.logger = loguru_logger
    
    def _setup_fallback(self) -> None:
        """Setup fallback Python logging."""
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(self.log_level)
        
        # Console handler
        if self.enable_console_logging:
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(self.log_level)
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
            )
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # File handler
        if self.enable_file_logging:
            log_file = self.log_dir / f"{self.name}.log"
            file_handler = logging.handlers.RotatingFileHandler(
                str(log_file),
                maxBytes=self.max_bytes,
                backupCount=self.backup_count
            )
            file_handler.setLevel(self.log_level)
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    @staticmethod
    def _json_format(record) -> str:
        """Format record as JSON."""
        log_data = {
            'timestamp': record['time'].isoformat(),
            'level': record['level'].name,
            'logger': record['name'],
            'function': record['function'],
            'line': record['line'],
            'message': record['message'],
            'extra': record.get('extra', {})
        }
        return json.dumps(log_data, default=str)
    
    def debug(self, message: str, context: Optional[Dict] = None) -> None:
        """Log debug message."""
        if context:
            self.logger.debug(f"{message} | {json.dumps(context)}")
        else:
            self.logger.debug(message)
    
    def info(self, message: str, context: Optional[Dict] = None) -> None:
        """Log info message."""
        if context:
            self.logger.info(f"{message} | {json.dumps(context)}")
        else:
            self.logger.info(message)
    
    def warning(self, message: str, context: Optional[Dict] = None) -> None:
        """Log warning message."""
        if context:
            self.logger.warning(f"{message} | {json.dumps(context)}")
        else:
            self.logger.warning(message)
    
    def error(self, message: str, context: Optional[Dict] = None, exc_info: bool = True) -> None:
        """Log error message."""
        if context:
            self.logger.error(f"{message} | {json.dumps(context)}", exc_info=exc_info)
        else:
            self.logger.error(message, exc_info=exc_info)
    
    def critical(self, message: str, context: Optional[Dict] = None) -> None:
        """Log critical message."""
        if context:
            self.logger.critical(f"{message} | {json.dumps(context)}")
        else:
            self.logger.critical(message)
    
    def exception(self, message: str, context: Optional[Dict] = None) -> None:
        """Log exception with traceback."""
        if context:
            self.logger.exception(f"{message} | {json.dumps(context)}")
        else:
            self.logger.exception(message)
    
    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        context: Optional[Dict] = None
    ) -> None:
        """
        Log API request/response.
        
        Args:
            method: HTTP method
            path: Request path
            status_code: Response status code
            duration_ms: Request duration in milliseconds
            context: Additional context
        """
        log_context = {
            'method': method,
            'path': path,
            'status_code': status_code,
            'duration_ms': f"{duration_ms:.2f}",
            'timestamp': datetime.now().isoformat()
        }
        
        if context:
            log_context.update(context)
        
        level = 'INFO' if status_code < 400 else 'WARNING' if status_code < 500 else 'ERROR'
        log_method = getattr(self, level.lower())
        log_method(f"HTTP {method} {path} {status_code}", log_context)
    
    def log_detection(
        self,
        track_id: int,
        class_name: str,
        confidence: float,
        position: tuple,
        speed: float = 0.0,
        lane: Optional[str] = None
    ) -> None:
        """Log vehicle detection."""
        context = {
            'track_id': track_id,
            'class': class_name,
            'confidence': f"{confidence:.3f}",
            'position': position,
            'speed': speed,
            'lane': lane,
            'timestamp': datetime.now().isoformat()
        }
        self.info(f"Detection: {class_name} (confidence: {confidence:.3f})", context)
    
    def log_performance(self, metric: PerformanceMetric) -> None:
        """Log performance metric."""
        self.info(f"Performance: {metric.name} ({metric.duration_ms:.2f}ms)", metric.to_dict())
    
    def timer(self, name: str, metadata: Optional[Dict] = None):
        """
        Context manager for timing code blocks.
        
        Usage:
            with logger.timer('name'):
                # Code to time
        """
        class Timer:
            def __init__(timer_self):
                timer_self.start = None
                timer_self.end = None
            
            def __enter__(timer_self):
                timer_self.start = time.time()
                return timer_self
            
            def __exit__(timer_self, exc_type, exc_val, exc_tb):
                timer_self.end = time.time()
                duration_ms = (timer_self.end - timer_self.start) * 1000
                metric = PerformanceMetric(name, duration_ms, metadata=metadata)
                self.log_performance(metric)
        
        return Timer()
    
    def function_logger(self, func: Callable) -> Callable:
        """
        Decorator for logging function calls with timing.
        
        Usage:
            @logger.function_logger
            def my_function(x, y):
                return x + y
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                self.info(f"Function completed: {func.__name__}", {
                    'duration_ms': f"{duration_ms:.2f}",
                    'status': 'success'
                })
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                self.error(f"Function failed: {func.__name__}", {
                    'duration_ms': f"{duration_ms:.2f}",
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                raise
        
        return wrapper
    
    def __repr__(self) -> str:
        """String representation."""
        return f"StructuredLogger(name={self.name}, level={self.log_level})"


# Global logger instance
_global_logger: Optional[StructuredLogger] = None


def get_logger(name: str = "traffic_system") -> StructuredLogger:
    """
    Get or create global logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        StructuredLogger instance
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = StructuredLogger(name)
    return _global_logger


def log_function_call(func: Callable) -> Callable:
    """
    Decorator to automatically log function calls.
    
    Usage:
        @log_function_call
        def my_function(x, y):
            return x + y
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger()
        start = time.time()
        try:
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start) * 1000
            logger.info(f"Function: {func.__name__}", {
                'duration_ms': f"{duration_ms:.2f}",
                'status': 'success'
            })
            return result
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            logger.error(f"Function: {func.__name__}", {
                'duration_ms': f"{duration_ms:.2f}",
                'error': str(e),
                'error_type': type(e).__name__
            })
            raise
    
    return wrapper


def log_performance(name: str) -> Callable:
    """
    Decorator to log function performance.
    
    Usage:
        @log_performance('my_operation')
        def expensive_operation():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            with logger.timer(name):
                return func(*args, **kwargs)
        
        return wrapper
    
    return decorator
