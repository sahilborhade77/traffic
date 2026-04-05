"""
FastAPI application with comprehensive API documentation.

Provides REST endpoints for:
- Health checks and system status
- Vehicle detection and tracking
- Signal timing control
- Traffic analytics and metrics
- Violation records
- Configuration management
"""

from fastapi import FastAPI, HTTPException, Query, Path as FastPath, Depends
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import json


# ============================================================================
# DATA MODELS
# ============================================================================

class SignalState(str, Enum):
    """Traffic signal states."""
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class ViolationType(str, Enum):
    """Traffic violation types."""
    RED_LIGHT = "red_light"
    SPEEDING = "speeding"
    ILLEGAL_TURN = "illegal_turn"
    OTHER = "other"


class VehicleClass(str, Enum):
    """Vehicle classification."""
    CAR = "car"
    TRUCK = "truck"
    MOTORCYCLE = "motorcycle"
    BUS = "bus"
    OTHER = "other"


class ControlMode(str, Enum):
    """Signal control modes."""
    FIXED = "fixed"
    ADAPTIVE = "adaptive"
    MANUAL = "manual"


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="System status")
    timestamp: datetime = Field(..., description="Response timestamp")
    version: str = Field(..., description="API version")
    uptime_seconds: float = Field(..., description="System uptime")


class VehicleDetection(BaseModel):
    """Vehicle detection record."""
    detection_id: int = Field(..., description="Unique detection ID")
    timestamp: datetime = Field(..., description="Detection timestamp")
    lane: str = Field(..., description="Lane name")
    vehicle_class: VehicleClass = Field(..., description="Vehicle type")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    bounding_box: Dict[str, int] = Field(..., description="Bounding box coordinates")
    speed: Optional[float] = Field(None, description="Estimated vehicle speed (km/h)")
    vehicle_id: Optional[str] = Field(None, description="Vehicle tracking ID")


class SignalStateResponse(BaseModel):
    """Traffic signal state."""
    lane: str = Field(..., description="Lane name")
    state: SignalState = Field(..., description="Current signal state")
    time_remaining: int = Field(..., description="Time remaining in current state (seconds)")
    cycle_position: int = Field(..., description="Position in signal cycle (0-120)")


class TrafficMetrics(BaseModel):
    """Real-time traffic metrics."""
    timestamp: datetime = Field(..., description="Metrics timestamp")
    lane: str = Field(..., description="Lane name")
    vehicle_count: int = Field(..., ge=0, description="Current vehicle count")
    congestion_level: float = Field(..., ge=0.0, le=1.0, description="Congestion level (0-1)")
    average_speed: float = Field(..., description="Average vehicle speed")
    throughput: int = Field(..., description="Vehicles processed per minute")
    wait_time: float = Field(..., description="Average wait time (seconds)")


class ViolationRecord(BaseModel):
    """Traffic violation record."""
    violation_id: int = Field(..., description="Unique violation ID")
    timestamp: datetime = Field(..., description="Violation timestamp")
    lane: str = Field(..., description="Lane name")
    vehicle_id: Optional[str] = Field(None, description="Vehicle ID")
    violation_type: ViolationType = Field(..., description="Type of violation")
    severity: int = Field(..., ge=1, le=5, description="Violation severity (1-5)")
    speed: Optional[float] = Field(None, description="Vehicle speed")
    processed: bool = Field(default=False, description="Violation processed status")


class SignalTimingConfig(BaseModel):
    """Signal timing configuration."""
    mode: ControlMode = Field(..., description="Control mode")
    cycle_length: int = Field(..., ge=60, le=240, description="Signal cycle length (seconds)")
    min_green: int = Field(..., ge=10, description="Minimum green time (seconds)")
    max_green: int = Field(..., le=200, description="Maximum green time (seconds)")
    yellow_duration: int = Field(..., ge=3, description="Yellow light duration (seconds)")


class SystemStatus(BaseModel):
    """System status and health information."""
    status: str = Field(..., description="Overall system status")
    uptime_seconds: float = Field(..., description="System uptime")
    cpu_usage: float = Field(..., ge=0, le=100, description="CPU usage percentage")
    memory_usage: float = Field(..., ge=0, le=100, description="Memory usage percentage")
    gpu_usage: Optional[float] = Field(None, ge=0, le=100, description="GPU usage percentage")
    active_cameras: int = Field(..., ge=0, description="Number of active cameras")
    database_latency_ms: float = Field(..., description="Database query latency")
    detections_per_second: float = Field(..., description="Current detection throughput")


class PageResponse(BaseModel):
    """Paginated response wrapper."""
    items: List[Any] = Field(..., description="Response items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Traffic Management System API",
    description="REST API for intelligent traffic management and monitoring",
    version="1.0.0",
    contact={
        "name": "Support Team",
        "email": "support@traffic-system.com",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)


# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="System Health Check",
    description="Check if the system is operational and responsive"
)
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "version": "1.0.0",
        "uptime_seconds": 3600.5,
    }


@app.get(
    "/status",
    response_model=SystemStatus,
    tags=["Monitoring"],
    summary="System Status",
    description="Get comprehensive system status and metrics"
)
def get_system_status():
    """Get system status."""
    return {
        "status": "operational",
        "uptime_seconds": 3600.5,
        "cpu_usage": 45.2,
        "memory_usage": 62.3,
        "gpu_usage": 78.5,
        "active_cameras": 4,
        "database_latency_ms": 12.5,
        "detections_per_second": 240.3,
    }


@app.get(
    "/ready",
    tags=["Health"],
    summary="Readiness Check",
    description="Check if the system is ready to accept requests"
)
def readiness_check():
    """Readiness check for Kubernetes."""
    return {"ready": True, "timestamp": datetime.now()}


# ============================================================================
# DETECTION ENDPOINTS
# ============================================================================

@app.get(
    "/detections",
    response_model=PageResponse,
    tags=["Detections"],
    summary="List Detections",
    description="Get paginated list of vehicle detections"
)
def list_detections(
    lane: Optional[str] = Query(None, description="Filter by lane"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
):
    """
    Get vehicle detections with optional filters.
    
    **Query Parameters:**
    - `lane`: Filter by lane name (North, South, East, West)
    - `start_time`: Filter detections after this time
    - `end_time`: Filter detections before this time
    - `page`: Page number for pagination
    - `page_size`: Number of items per page
    
    **Response:** Paginated list of vehicle detections
    """
    detections = [
        {
            "detection_id": i,
            "timestamp": datetime.now() - timedelta(seconds=i*10),
            "lane": lane or "North",
            "vehicle_class": "car",
            "confidence": 0.95,
            "bounding_box": {"x_min": 100, "y_min": 100, "x_max": 150, "y_max": 150},
            "speed": 25.5,
            "vehicle_id": f"V{i:04d}",
        }
        for i in range(1, 11)
    ]
    
    return {
        "items": detections,
        "total": len(detections),
        "page": page,
        "page_size": page_size,
        "total_pages": (len(detections) + page_size - 1) // page_size,
    }


@app.get(
    "/detections/{detection_id}",
    response_model=VehicleDetection,
    tags=["Detections"],
    summary="Get Detection Details",
    description="Get detailed information about a specific vehicle detection"
)
def get_detection(detection_id: int = FastPath(..., gt=0, description="Detection ID")):
    """Get specific detection."""
    return {
        "detection_id": detection_id,
        "timestamp": datetime.now(),
        "lane": "North",
        "vehicle_class": "car",
        "confidence": 0.95,
        "bounding_box": {"x_min": 100, "y_min": 100, "x_max": 150, "y_max": 150},
        "speed": 25.5,
        "vehicle_id": f"V{detection_id:04d}",
    }


# ============================================================================
# SIGNAL CONTROL ENDPOINTS
# ============================================================================

@app.get(
    "/signals",
    response_model=List[SignalStateResponse],
    tags=["Signals"],
    summary="Get All Signal States",
    description="Get current state of all traffic signals"
)
def get_all_signals():
    """Get all signal states."""
    return [
        {
            "lane": "North",
            "state": "green",
            "time_remaining": 35,
            "cycle_position": 40,
        },
        {
            "lane": "South",
            "state": "red",
            "time_remaining": 55,
            "cycle_position": 80,
        },
        {
            "lane": "East",
            "state": "red",
            "time_remaining": 55,
            "cycle_position": 120,
        },
        {
            "lane": "West",
            "state": "green",
            "time_remaining": 35,
            "cycle_position": 40,
        },
    ]


@app.get(
    "/signals/{lane}",
    response_model=SignalStateResponse,
    tags=["Signals"],
    summary="Get Signal State",
    description="Get current state of a specific traffic signal"
)
def get_signal_state(lane: str = FastPath(..., description="Lane name")):
    """Get signal state for specific lane."""
    return {
        "lane": lane,
        "state": "green",
        "time_remaining": 35,
        "cycle_position": 40,
    }


@app.post(
    "/signals/{lane}/control",
    tags=["Signals"],
    summary="Control Signal",
    description="Manually control a specific traffic signal"
)
def control_signal(
    lane: str = FastPath(..., description="Lane name"),
    state: SignalState = Query(..., description="Desired signal state"),
    duration: int = Query(..., gt=0, description="Duration in seconds"),
):
    """
    Manually control a traffic signal.
    
    **Parameters:**
    - `lane`: Lane to control (North, South, East, West)
    - `state`: Desired state (green, yellow, red)
    - `duration`: How long to maintain the state
    
    **Returns:** Confirmation of control action
    """
    return {
        "success": True,
        "lane": lane,
        "state": state,
        "duration": duration,
        "timestamp": datetime.now(),
    }


# ============================================================================
# METRICS & ANALYTICS ENDPOINTS
# ============================================================================

@app.get(
    "/metrics/{lane}",
    response_model=TrafficMetrics,
    tags=["Analytics"],
    summary="Get Lane Metrics",
    description="Get real-time traffic metrics for a specific lane"
)
def get_lane_metrics(lane: str = FastPath(..., description="Lane name")):
    """Get real-time metrics for a lane."""
    return {
        "timestamp": datetime.now(),
        "lane": lane,
        "vehicle_count": 12,
        "congestion_level": 0.35,
        "average_speed": 24.5,
        "throughput": 45,
        "wait_time": 32.5,
    }


@app.get(
    "/metrics/system/aggregate",
    tags=["Analytics"],
    summary="System-wide Metrics",
    description="Get aggregated metrics across all lanes"
)
def get_system_metrics(
    time_window: int = Query(3600, description="Time window in seconds")
):
    """Get system-wide metrics."""
    return {
        "timestamp": datetime.now(),
        "total_vehicles": 847,
        "average_congestion": 0.32,
        "average_wait_time": 38.2,
        "overall_throughput": 1840,
        "time_window_seconds": time_window,
    }


@app.get(
    "/analytics/hourly",
    tags=["Analytics"],
    summary="Hourly Statistics",
    description="Get hourly traffic statistics"
)
def get_hourly_statistics(
    lane: Optional[str] = Query(None, description="Filter by lane"),
    hours: int = Query(24, ge=1, le=168, description="Number of hours to retrieve"),
):
    """Get hourly statistics."""
    return {
        "data": [
            {
                "hour": datetime.now() - timedelta(hours=h),
                "lane": lane or "All",
                "vehicle_count": 150 + h * 10,
                "avg_speed": 20 + h * 0.5,
                "violations": 3 + h,
            }
            for h in range(hours)
        ],
        "total_hours": hours,
    }


# ============================================================================
# VIOLATION ENDPOINTS
# ============================================================================

@app.get(
    "/violations",
    response_model=PageResponse,
    tags=["Violations"],
    summary="List Violations",
    description="Get paginated list of traffic violations"
)
def list_violations(
    violation_type: Optional[ViolationType] = Query(None, description="Filter by type"),
    processed: Optional[bool] = Query(None, description="Filter by processed status"),
    min_severity: int = Query(1, ge=1, le=5, description="Minimum severity level"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
):
    """
    Get traffic violations with filtering options.
    
    **Query Parameters:**
    - `violation_type`: Filter by type (red_light, speeding, illegal_turn, other)
    - `processed`: Filter by processing status
    - `min_severity`: Minimum violation severity (1-5)
    - `page`: Page number
    - `page_size`: Items per page
    """
    violations = [
        {
            "violation_id": i,
            "timestamp": datetime.now() - timedelta(hours=i),
            "lane": "North",
            "vehicle_id": f"V{i:04d}",
            "violation_type": "red_light",
            "severity": 3,
            "speed": 45.0,
            "processed": i % 3 == 0,
        }
        for i in range(1, 11)
    ]
    
    return {
        "items": violations,
        "total": len(violations),
        "page": page,
        "page_size": page_size,
        "total_pages": (len(violations) + page_size - 1) // page_size,
    }


@app.post(
    "/violations/{violation_id}/process",
    tags=["Violations"],
    summary="Mark Violation as Processed",
    description="Mark a violation record as processed"
)
def process_violation(
    violation_id: int = FastPath(..., gt=0, description="Violation ID"),
    notes: Optional[str] = Query(None, description="Processing notes"),
):
    """Mark violation as processed."""
    return {
        "success": True,
        "violation_id": violation_id,
        "processed": True,
        "timestamp": datetime.now(),
        "notes": notes,
    }


# ============================================================================
# CONFIGURATION ENDPOINTS
# ============================================================================

@app.get(
    "/config/signals",
    response_model=SignalTimingConfig,
    tags=["Configuration"],
    summary="Get Signal Configuration",
    description="Get current signal timing configuration"
)
def get_signal_config():
    """Get signal timing configuration."""
    return {
        "mode": "adaptive",
        "cycle_length": 120,
        "min_green": 20,
        "max_green": 80,
        "yellow_duration": 5,
    }


@app.put(
    "/config/signals",
    response_model=SignalTimingConfig,
    tags=["Configuration"],
    summary="Update Signal Configuration",
    description="Update signal timing configuration"
)
def update_signal_config(config: SignalTimingConfig):
    """Update signal configuration."""
    return config.dict()


# ============================================================================
# CUSTOM OPENAPI SCHEMA
# ============================================================================

def custom_openapi():
    """Generate custom OpenAPI schema with additional documentation."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Traffic Management System API",
        version="1.0.0",
        description="""
        Comprehensive REST API for intelligent traffic management and monitoring.
        
        ## Authentication
        Currently, the API does not require authentication. In production,
        implement OAuth2 or API key authentication.
        
        ## Rate Limiting
        - Standard: 1000 requests/hour
        - Premium: 10000 requests/hour
        - Enterprise: Unlimited
        
        ## Webhooks
        Subscribe to real-time events:
        - `detection.created`: New vehicle detected
        - `violation.recorded`: Traffic violation recorded
        - `signal.changed`: Signal state changed
        
        ## API Versioning
        Current version: v1
        Base URL: `/api/v1/`
        
        ## Error Handling
        All errors return JSON with:
        - `error`: Error code
        - `message`: Human-readable message
        - `timestamp`: When error occurred
        """,
        routes=app.routes,
    )
    
    openapi_schema["info"]["x-logo"] = {
        "url": "https://example.com/logo.png"
    }
    
    # Add servers
    openapi_schema["servers"] = [
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        },
        {
            "url": "https://api.traffic-system.com",
            "description": "Production server"
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/docs", include_in_schema=False)
def get_documentation():
    """Swagger UI documentation."""
    return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Traffic Management API - Swagger UI</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui.css">
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui-bundle.js"></script>
            <script>
            SwaggerUIBundle({
                url: "/openapi.json",
                dom_id: '#swagger-ui',
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
                layout: "BaseLayout"
            })
            </script>
        </body>
        </html>
    """)


# ============================================================================
# EXAMPLE REQUESTS
# ============================================================================

"""
EXAMPLE API REQUESTS

## Health Check
GET /health
Response: {
  "status": "healthy",
  "timestamp": "2024-01-15T12:00:00Z",
  "version": "1.0.0",
  "uptime_seconds": 3600.5
}

## Get Signal States
GET /signals
Response: [
  {
    "lane": "North",
    "state": "green",
    "time_remaining": 35,
    "cycle_position": 40
  },
  ...
]

## List Detections
GET /detections?lane=North&page=1&page_size=50
Response: {
  "items": [...],
  "total": 1250,
  "page": 1,
  "page_size": 50,
  "total_pages": 25
}

## Control Signal
POST /signals/North/control?state=green&duration=45
Response: {
  "success": true,
  "lane": "North",
  "state": "green",
  "duration": 45,
  "timestamp": "2024-01-15T12:00:00Z"
}

## Get Metrics
GET /metrics/North
Response: {
  "timestamp": "2024-01-15T12:00:00Z",
  "lane": "North",
  "vehicle_count": 12,
  "congestion_level": 0.35,
  "average_speed": 24.5,
  "throughput": 45,
  "wait_time": 32.5
}
"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
