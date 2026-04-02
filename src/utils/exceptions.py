"""
Custom Exceptions for Traffic Management System

Provides a hierarchy of custom exceptions for comprehensive error handling
across all components: camera, model, API, prediction, and infrastructure.

Usage:
    from src.utils.exceptions import CameraError, ModelLoadError, APIError
    
    try:
        camera = CameraManager()
    except CameraDisconnected as e:
        logger.error(f"Camera failure: {e.error_message}")
        attempt_recovery(e.retry_count)

Author: Traffic Intelligence Team
Version: 1.0.0
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for an error."""
    component: str
    operation: str
    timestamp: str = None
    metadata: Dict[str, Any] = None
    retry_count: int = 0
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'component': self.component,
            'operation': self.operation,
            'timestamp': self.timestamp,
            'metadata': self.metadata or {},
            'retry_count': self.retry_count,
            'suggestion': self.suggestion
        }


class TrafficSystemError(Exception):
    """Base exception for all traffic system errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN",
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize exception.
        
        Args:
            message: Human-readable error message
            error_code: Unique error code for tracking
            severity: Error severity level
            context: Additional error context
            original_exception: Original exception that caused this
        """
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.context = context
        self.original_exception = original_exception
        
        super().__init__(self.message)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging/API responses."""
        return {
            'error_code': self.error_code,
            'message': self.message,
            'severity': self.severity.value,
            'context': self.context.to_dict() if self.context else None,
            'original_error': str(self.original_exception) if self.original_exception else None
        }
    
    def __str__(self) -> str:
        """String representation."""
        return f"[{self.error_code}] {self.message}"


# ============================================================================
# CAMERA & VIDEO ERRORS
# ============================================================================

class CameraError(TrafficSystemError):
    """Base exception for camera-related errors."""
    pass


class CameraNotFoundError(CameraError):
    """Camera file or URL not found."""
    
    def __init__(self, camera_id: str, path: str, **kwargs):
        super().__init__(
            message=f"Camera '{camera_id}' not found at: {path}",
            error_code="CAMERA_NOT_FOUND",
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
        self.camera_id = camera_id
        self.path = path


class CameraDisconnectedError(CameraError):
    """Camera unexpectedly disconnected."""
    
    def __init__(self, camera_id: str, reason: str = "Unknown", **kwargs):
        super().__init__(
            message=f"Camera '{camera_id}' disconnected: {reason}",
            error_code="CAMERA_DISCONNECTED",
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
        self.camera_id = camera_id
        self.reason = reason


class CameraTimeoutError(CameraError):
    """Camera did not respond within timeout period."""
    
    def __init__(self, camera_id: str, timeout_sec: float, **kwargs):
        super().__init__(
            message=f"Camera '{camera_id}' timeout after {timeout_sec}s",
            error_code="CAMERA_TIMEOUT",
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )
        self.camera_id = camera_id
        self.timeout_sec = timeout_sec


class CameraFrameError(CameraError):
    """Error reading frame from camera."""
    
    def __init__(self, camera_id: str, frame_number: int, reason: str, **kwargs):
        super().__init__(
            message=f"Camera '{camera_id}' frame #{frame_number} error: {reason}",
            error_code="CAMERA_FRAME_ERROR",
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )
        self.camera_id = camera_id
        self.frame_number = frame_number


class VideoProcessingError(CameraError):
    """Error processing video stream."""
    
    def __init__(self, reason: str, operation: str = "processing", **kwargs):
        super().__init__(
            message=f"Video {operation} error: {reason}",
            error_code="VIDEO_PROCESSING_ERROR",
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


# ============================================================================
# MODEL & INFERENCE ERRORS
# ============================================================================

class ModelError(TrafficSystemError):
    """Base exception for model-related errors."""
    pass


class ModelNotFoundError(ModelError):
    """Model file not found."""
    
    def __init__(self, model_name: str, path: str, **kwargs):
        super().__init__(
            message=f"Model '{model_name}' not found at: {path}",
            error_code="MODEL_NOT_FOUND",
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )
        self.model_name = model_name
        self.path = path


class ModelLoadError(ModelError):
    """Error loading model from file."""
    
    def __init__(self, model_name: str, reason: str, **kwargs):
        super().__init__(
            message=f"Failed to load model '{model_name}': {reason}",
            error_code="MODEL_LOAD_ERROR",
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )
        self.model_name = model_name
        self.reason = reason


class ModelInferenceError(ModelError):
    """Error during model inference."""
    
    def __init__(self, model_name: str, reason: str, input_shape: tuple = None, **kwargs):
        msg = f"Inference failed for '{model_name}': {reason}"
        if input_shape:
            msg += f" (input shape: {input_shape})"
        
        super().__init__(
            message=msg,
            error_code="MODEL_INFERENCE_ERROR",
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
        self.model_name = model_name
        self.input_shape = input_shape


class OutOfMemoryError(ModelError):
    """GPU/CPU out of memory."""
    
    def __init__(self, device: str = "GPU", available_mb: int = 0, **kwargs):
        super().__init__(
            message=f"{device} out of memory (available: {available_mb}MB)",
            error_code="OUT_OF_MEMORY",
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )
        self.device = device
        self.available_mb = available_mb


class CudaError(ModelError):
    """CUDA/GPU error."""
    
    def __init__(self, reason: str, **kwargs):
        super().__init__(
            message=f"CUDA error: {reason}",
            error_code="CUDA_ERROR",
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )


# ============================================================================
# API & COMMUNICATION ERRORS
# ============================================================================

class APIError(TrafficSystemError):
    """Base exception for API-related errors."""
    pass


class APIConnectionError(APIError):
    """Failed to connect to API endpoint."""
    
    def __init__(self, endpoint: str, reason: str, **kwargs):
        super().__init__(
            message=f"API connection failed to {endpoint}: {reason}",
            error_code="API_CONNECTION_ERROR",
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
        self.endpoint = endpoint


class APITimeoutError(APIError):
    """API request timeout."""
    
    def __init__(self, endpoint: str, timeout_sec: float, **kwargs):
        super().__init__(
            message=f"API request to {endpoint} timeout after {timeout_sec}s",
            error_code="API_TIMEOUT",
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )
        self.endpoint = endpoint
        self.timeout_sec = timeout_sec


class APIResponseError(APIError):
    """Invalid API response."""
    
    def __init__(self, endpoint: str, status_code: int, reason: str, **kwargs):
        super().__init__(
            message=f"API {endpoint} returned {status_code}: {reason}",
            error_code="API_RESPONSE_ERROR",
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )
        self.endpoint = endpoint
        self.status_code = status_code


class DatabaseError(APIError):
    """Database operation failed."""
    
    def __init__(self, operation: str, reason: str, **kwargs):
        super().__init__(
            message=f"Database {operation} failed: {reason}",
            error_code="DATABASE_ERROR",
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


# ============================================================================
# PREDICTION & ANALYSIS ERRORS
# ============================================================================

class PredictionError(TrafficSystemError):
    """Base exception for prediction-related errors."""
    pass


class TrainingError(PredictionError):
    """Error during model training."""
    
    def __init__(self, model_name: str, reason: str, epoch: int = None, **kwargs):
        msg = f"Training failed for '{model_name}': {reason}"
        if epoch:
            msg += f" at epoch {epoch}"
        
        super().__init__(
            message=msg,
            error_code="TRAINING_ERROR",
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
        self.model_name = model_name
        self.epoch = epoch


class PredictionDataError(PredictionError):
    """Invalid data for prediction."""
    
    def __init__(self, reason: str, required_shape: tuple = None, **kwargs):
        msg = f"Prediction data error: {reason}"
        if required_shape:
            msg += f" (required shape: {required_shape})"
        
        super().__init__(
            message=msg,
            error_code="PREDICTION_DATA_ERROR",
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class CacheError(PredictionError):
    """Cache operation failed."""
    
    def __init__(self, operation: str, reason: str, **kwargs):
        super().__init__(
            message=f"Cache {operation} failed: {reason}",
            error_code="CACHE_ERROR",
            severity=ErrorSeverity.LOW,
            **kwargs
        )
        self.operation = operation


# ============================================================================
# CONFIGURATION & SETUP ERRORS
# ============================================================================

class ConfigError(TrafficSystemError):
    """Configuration error."""
    
    def __init__(self, config_file: str, reason: str, **kwargs):
        super().__init__(
            message=f"Configuration error in {config_file}: {reason}",
            error_code="CONFIG_ERROR",
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )
        self.config_file = config_file


class DependencyError(TrafficSystemError):
    """Missing or incompatible dependency."""
    
    def __init__(self, package_name: str, version: str = None, **kwargs):
        msg = f"Dependency error: {package_name}"
        if version:
            msg += f" (required: {version})"
        
        super().__init__(
            message=msg,
            error_code="DEPENDENCY_ERROR",
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )
        self.package_name = package_name
        self.version = version


# ============================================================================
# RECOVERY & RETRY MECHANISMS
# ============================================================================

class RecoverableError(TrafficSystemError):
    """Error that can be recovered with retry."""
    
    def __init__(
        self,
        message: str,
        max_retries: int = 3,
        retry_delay_sec: float = 1.0,
        **kwargs
    ):
        super().__init__(message=message, **kwargs)
        self.max_retries = max_retries
        self.retry_delay_sec = retry_delay_sec
        self.retry_count = 0
    
    def should_retry(self) -> bool:
        """Check if should retry."""
        return self.retry_count < self.max_retries
    
    def increment_retry(self) -> None:
        """Increment retry counter."""
        self.retry_count += 1


class FatalError(TrafficSystemError):
    """Fatal error that requires system shutdown."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="FATAL_ERROR",
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )


# ============================================================================
# ERROR HANDLING UTILITIES
# ============================================================================

def create_error_response(exception: TrafficSystemError) -> Dict:
    """
    Create API error response from exception.
    
    Args:
        exception: TrafficSystemError instance
        
    Returns:
        Dictionary ready for API response
    """
    return {
        'error': exception.to_dict(),
        'status': 'error'
    }


def is_recoverable(exception: Exception) -> bool:
    """
    Check if exception is recoverable.
    
    Args:
        exception: Exception to check
        
    Returns:
        True if recoverable
    """
    recoverable_errors = (
        CameraDisconnectedError,
        CameraTimeoutError,
        CameraFrameError,
        APITimeoutError,
        RecoverableError,
        ConnectionError,
        TimeoutError,
    )
    
    return isinstance(exception, recoverable_errors)


def get_error_suggestion(exception: TrafficSystemError) -> str:
    """
    Get user-friendly suggestion for error.
    
    Args:
        exception: TrafficSystemError instance
        
    Returns:
        Suggested action
    """
    suggestions = {
        'CAMERA_NOT_FOUND': 'Check camera URL/path configuration and network connectivity',
        'CAMERA_DISCONNECTED': 'Verify camera is powered on and connected to network',
        'MODEL_NOT_FOUND': 'Download model weights and place in models/ directory',
        'MODEL_LOAD_ERROR': 'Verify model format matches expected version',
        'OUT_OF_MEMORY': 'Reduce batch size or model resolution',
        'CUDA_ERROR': 'Update GPU drivers or fall back to CPU processing',
        'API_TIMEOUT': 'Check network connectivity and backend service status',
        'DATABASE_ERROR': 'Verify database is running and accessible',
        'CONFIG_ERROR': 'Review configuration file syntax and required fields',
    }
    
    return suggestions.get(exception.error_code, 'Check logs for more details')
