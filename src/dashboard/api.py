#!/usr/bin/env python3
"""
FastAPI REST API for Smart Traffic Management System

Endpoints:
- /api/traffic/status - Real-time traffic status
- /api/analytics/hourly - Hourly statistics
- /api/analytics/daily - Daily statistics
- /api/analytics/peak-hours - Peak hour analysis
- /api/camera/feed - Live camera feed stream
- /api/camera/snapshot - Single frame snapshot
- /api/signal/status - Current signal state
- /api/signal/control - Adjust signal timing
- /api/violations - Traffic violation records
- /api/health - System health status
"""

import logging
import json
import cv2
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Smart Traffic Management API",
    description="Real-time traffic monitoring and control system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================== Pydantic Models =====================


class TrafficStatusResponse(BaseModel):
    """Response model for traffic status."""
    timestamp: str
    lane: str
    vehicle_count: int
    avg_speed: float
    wait_time: float
    congestion_level: str
    violations_count: int


class HourlyStatsResponse(BaseModel):
    """Response model for hourly statistics."""
    datetime: str
    hour: int
    lane: str
    total_vehicles: int
    avg_wait_time: float
    total_violations: int
    peak_hour: bool
    congestion_level: str


class DailyStatsResponse(BaseModel):
    """Response model for daily statistics."""
    date: str
    day_of_week: str
    total_vehicles: int
    avg_wait_time: float
    total_violations: int
    peak_hours: List[int]
    busiest_hour: Optional[int]


class SignalControlRequest(BaseModel):
    """Request model for signal control."""
    lane: str
    action: str  # 'extend', 'shorten', 'set_timing'
    duration: Optional[int] = None
    green_time: Optional[int] = None
    red_time: Optional[int] = None


class SignalStatusResponse(BaseModel):
    """Response model for signal status."""
    timestamp: str
    lane: str
    state: str  # 'RED', 'GREEN', 'YELLOW'
    time_remaining: int
    phase: int


class ViolationRecord(BaseModel):
    """Model for traffic violations."""
    violation_id: str
    timestamp: str
    lane: str
    vehicle_class: str
    violation_type: str
    severity: str
    speed: Optional[float] = None
    position: Optional[List[float]] = None


class HealthStatus(BaseModel):
    """Model for system health status."""
    status: str
    detector_active: bool
    tracker_active: bool
    api_fps: float
    memory_usage: float
    uptime_seconds: float


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")


# Global instances
manager = ConnectionManager()

# Mock state (would be connected to real systems)
traffic_state = {
    'North': {'vehicle_count': 0, 'avg_speed': 0.0, 'wait_time': 0.0},
    'South': {'vehicle_count': 0, 'avg_speed': 0.0, 'wait_time': 0.0},
    'East': {'vehicle_count': 0, 'avg_speed': 0.0, 'wait_time': 0.0},
    'West': {'vehicle_count': 0, 'avg_speed': 0.0, 'wait_time': 0.0},
}

signal_state = {
    'North': {'state': 'RED', 'time_remaining': 30, 'phase': 0},
    'South': {'state': 'GREEN', 'time_remaining': 25, 'phase': 0},
    'East': {'state': 'RED', 'time_remaining': 30, 'phase': 0},
    'West': {'state': 'GREEN', 'time_remaining': 25, 'phase': 0},
}

system_start_time = datetime.now()

# ===================== Utility Functions =====================


def get_system_uptime() -> float:
    """Get system uptime in seconds."""
    return (datetime.now() - system_start_time).total_seconds()


def get_congestion_level(vehicle_count: int, avg_speed: float) -> str:
    """Determine congestion level based on metrics."""
    if vehicle_count < 10 and avg_speed > 8.0:
        return 'low'
    elif vehicle_count < 20 and avg_speed > 5.0:
        return 'medium'
    elif vehicle_count > 40 or avg_speed < 2.0:
        return 'critical'
    else:
        return 'high'


async def simulate_traffic_updates():
    """Simulate traffic updates (for demo purposes)."""
    while True:
        try:
            # Simulate traffic data changes
            for lane in traffic_state:
                traffic_state[lane]['vehicle_count'] = max(
                    0,
                    traffic_state[lane]['vehicle_count'] + np.random.randint(-2, 5)
                )
                traffic_state[lane]['avg_speed'] = max(
                    0.0,
                    traffic_state[lane]['avg_speed'] + np.random.uniform(-1, 1)
                )
                traffic_state[lane]['wait_time'] = max(
                    0.0,
                    traffic_state[lane]['wait_time'] + np.random.uniform(-5, 5)
                )

            # Broadcast update
            message = {
                'type': 'traffic_update',
                'timestamp': datetime.now().isoformat(),
                'data': traffic_state
            }
            await manager.broadcast(message)

            await asyncio.sleep(5)  # Update every 5 seconds

        except Exception as e:
            logger.error(f"Error in traffic simulation: {e}")
            await asyncio.sleep(5)


# ===================== Root Endpoint =====================


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "Smart Traffic Management API",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "/docs",
        "endpoints": {
            "traffic": "/api/traffic/status",
            "analytics": "/api/analytics/",
            "camera": "/api/camera/",
            "signal": "/api/signal/",
            "violations": "/api/violations",
            "health": "/api/health"
        }
    }


# ===================== Health & Status =====================


@app.get("/api/health", response_model=HealthStatus)
async def health_check():
    """Get system health status."""
    return {
        "status": "healthy",
        "detector_active": True,
        "tracker_active": True,
        "api_fps": 30.0,
        "memory_usage": 45.2,
        "uptime_seconds": get_system_uptime()
    }


# ===================== Traffic Status Endpoints =====================


@app.get("/api/traffic/status", response_model=List[TrafficStatusResponse])
async def get_traffic_status(lane: Optional[str] = None):
    """
    Get real-time traffic status for all lanes or a specific lane.

    Query Parameters:
    - lane: Optional lane filter (North, South, East, West)

    Returns:
    - List of traffic status objects
    """
    lanes = [lane] if lane else list(traffic_state.keys())
    results = []

    for current_lane in lanes:
        if current_lane not in traffic_state:
            raise HTTPException(status_code=404, detail=f"Lane '{current_lane}' not found")

        state = traffic_state[current_lane]
        congestion = get_congestion_level(
            state['vehicle_count'],
            state['avg_speed']
        )

        results.append(
            TrafficStatusResponse(
                timestamp=datetime.now().isoformat(),
                lane=current_lane,
                vehicle_count=int(state['vehicle_count']),
                avg_speed=float(state['avg_speed']),
                wait_time=float(state['wait_time']),
                congestion_level=congestion,
                violations_count=np.random.randint(0, 5)
            )
        )

    return results


@app.get("/api/traffic/congestion")
async def get_congestion_index():
    """Get overall congestion index (0-1 scale)."""
    congestion_levels = get_traffic_status()
    level_map = {'low': 0.2, 'medium': 0.5, 'high': 0.75, 'critical': 1.0}
    indices = [level_map.get(s.congestion_level, 0.5) for s in congestion_levels]
    avg_index = np.mean(indices) if indices else 0.0

    return {
        "timestamp": datetime.now().isoformat(),
        "congestion_index": float(avg_index),
        "level": (
            "critical" if avg_index > 0.75 else
            "high" if avg_index > 0.5 else
            "medium" if avg_index > 0.2 else
            "low"
        )
    }


# ===================== Real-time WebSocket =====================


@app.websocket("/api/ws/traffic")
async def websocket_traffic(websocket: WebSocket):
    """
    WebSocket connection for real-time traffic updates.

    Returns stream of traffic status updates.
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                await manager.broadcast({
                    "type": "message",
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ===================== Analytics Endpoints =====================


@app.get("/api/analytics/hourly", response_model=List[HourlyStatsResponse])
async def get_hourly_statistics(lane: Optional[str] = None):
    """
    Get hourly traffic statistics.

    Query Parameters:
    - lane: Optional lane filter

    Returns:
    - List of hourly statistics
    """
    now = datetime.now()

    lanes = [lane] if lane else list(traffic_state.keys())
    results = []

    for current_lane in lanes:
        state = traffic_state[current_lane]
        congestion = get_congestion_level(
            state['vehicle_count'],
            state['avg_speed']
        )

        results.append(
            HourlyStatsResponse(
                datetime=now.isoformat(),
                hour=now.hour,
                lane=current_lane,
                total_vehicles=int(state['vehicle_count']) * 6,  # Scale up
                avg_wait_time=float(state['wait_time']),
                total_violations=np.random.randint(0, 3),
                peak_hour=(now.hour in [8, 9, 17, 18, 19]),
                congestion_level=congestion
            )
        )

    return results


@app.get("/api/analytics/daily", response_model=DailyStatsResponse)
async def get_daily_statistics(date: Optional[str] = None):
    """
    Get daily traffic statistics.

    Query Parameters:
    - date: Optional date (YYYY-MM-DD). Defaults to today.

    Returns:
    - Daily statistics object
    """
    target_date = date or datetime.now().date().isoformat()
    target_dt = datetime.fromisoformat(target_date)

    # Calculate statistics
    total_vehicles = sum(
        traffic_state[lane]['vehicle_count'] * 24 * 6
        for lane in traffic_state
    )
    avg_wait_time = np.mean([
        traffic_state[lane]['wait_time']
        for lane in traffic_state
    ])

    # Simulate peak hours
    peak_hours = [8, 9, 17, 18, 19]

    return DailyStatsResponse(
        date=target_date,
        day_of_week=target_dt.strftime('%A'),
        total_vehicles=int(total_vehicles),
        avg_wait_time=float(avg_wait_time),
        total_violations=np.random.randint(10, 50),
        peak_hours=peak_hours,
        busiest_hour=18
    )


@app.get("/api/analytics/peak-hours")
async def get_peak_hours(limit: int = Query(5, ge=1, le=24)):
    """
    Get peak traffic hours.

    Query Parameters:
    - limit: Number of peak hours to return (default: 5, max: 24)

    Returns:
    - List of peak hours with vehicle counts
    """
    peak_hours = [
        {"hour": h, "vehicle_count": np.random.randint(100, 300)}
        for h in [7, 8, 9, 12, 17, 18, 19]
    ]

    return {
        "date": datetime.now().date().isoformat(),
        "peak_hours": sorted(
            peak_hours,
            key=lambda x: x['vehicle_count'],
            reverse=True
        )[:limit]
    }


@app.get("/api/analytics/trends")
async def get_traffic_trends(days: int = Query(7, ge=1, le=30)):
    """
    Get traffic trends over past N days.

    Query Parameters:
    - days: Number of days to analyze (default: 7, max: 30)

    Returns:
    - Trend analysis
    """
    trends = []
    for i in range(days):
        past_date = datetime.now() - timedelta(days=i)
        trends.append({
            "date": past_date.date().isoformat(),
            "avg_vehicles": np.random.randint(500, 2000),
            "avg_wait_time": np.random.uniform(20, 120),
            "total_violations": np.random.randint(5, 50)
        })

    return {
        "period_days": days,
        "trends": sorted(trends, key=lambda x: x['date'])
    }


# ===================== Camera Endpoints =====================


@app.get("/api/camera/snapshot")
async def get_camera_snapshot(lane: Optional[str] = None):
    """
    Get current snapshot from camera.

    Query Parameters:
    - lane: Optional lane to capture from

    Returns:
    - JPEG image
    """
    # Create a dummy frame for demo
    height, width = 480, 640
    frame = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)

    # Add lane text
    if lane:
        cv2.putText(
            frame,
            f"Lane: {lane}",
            (50, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            (0, 255, 0),
            2
        )

    # Add timestamp
    cv2.putText(
        frame,
        f"Snapshot: {datetime.now().isoformat()}",
        (50, height - 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 255, 255),
        2
    )

    # Encode to JPEG
    ret, buffer = cv2.imencode('.jpg', frame)
    if not ret:
        raise HTTPException(status_code=500, detail="Failed to encode image")

    return StreamingResponse(
        iter([buffer.tobytes()]),
        media_type="image/jpeg"
    )


@app.websocket("/api/ws/camera")
async def websocket_camera(websocket: WebSocket, lane: Optional[str] = None):
    """
    WebSocket stream for live camera feed.

    Query Parameters:
    - lane: Lane to stream from

    Returns:
    - MJPEG stream via JSON frames
    """
    await websocket.accept()
    try:
        while True:
            # Generate dummy frame
            frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)

            # Add info
            cv2.putText(
                frame,
                f"Lane: {lane or 'North'} - {datetime.now().strftime('%H:%M:%S')}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )

            # Encode
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                await websocket.send_bytes(buffer.tobytes())

            await asyncio.sleep(0.033)  # 30 FPS

    except WebSocketDisconnect:
        logger.info(f"Camera feed disconnected")
    except Exception as e:
        logger.error(f"Camera stream error: {e}")


# ===================== Signal Control Endpoints =====================


@app.get("/api/signal/status", response_model=List[SignalStatusResponse])
async def get_signal_status(lane: Optional[str] = None):
    """
    Get current signal status for all lanes or specific lane.

    Query Parameters:
    - lane: Optional lane filter

    Returns:
    - List of signal status objects
    """
    lanes = [lane] if lane else list(signal_state.keys())
    results = []

    for current_lane in lanes:
        if current_lane not in signal_state:
            raise HTTPException(status_code=404, detail=f"Lane '{current_lane}' not found")

        state = signal_state[current_lane]
        results.append(
            SignalStatusResponse(
                timestamp=datetime.now().isoformat(),
                lane=current_lane,
                state=state['state'],
                time_remaining=state['time_remaining'],
                phase=state['phase']
            )
        )

    return results


@app.post("/api/signal/control")
async def control_signal(request: SignalControlRequest):
    """
    Control traffic signal timing.

    Request body:
    - lane: Lane name
    - action: 'extend', 'shorten', or 'set_timing'
    - duration: Duration adjustment (seconds)
    - green_time: Green phase duration
    - red_time: Red phase duration

    Returns:
    - Control confirmation
    """
    if request.lane not in signal_state:
        raise HTTPException(status_code=404, detail=f"Lane '{request.lane}' not found")

    state = signal_state[request.lane]

    if request.action == 'extend' and request.duration:
        state['time_remaining'] = min(120, state['time_remaining'] + request.duration)
        action_desc = f"Extended by {request.duration}s"

    elif request.action == 'shorten' and request.duration:
        state['time_remaining'] = max(5, state['time_remaining'] - request.duration)
        action_desc = f"Shortened by {request.duration}s"

    elif request.action == 'set_timing' and request.green_time:
        state['time_remaining'] = request.green_time
        action_desc = f"Set to {request.green_time}s"

    else:
        raise HTTPException(status_code=400, detail="Invalid action or parameters")

    return {
        "status": "success",
        "lane": request.lane,
        "action": action_desc,
        "new_timing": state['time_remaining'],
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/signal/adaptive")
async def enable_adaptive_control(lane: Optional[str] = None):
    """
    Enable adaptive signal control based on traffic.

    Query Parameters:
    - lane: Optional lane to enable for. All if not specified.

    Returns:
    - Confirmation of adaptive control enabled
    """
    lanes = [lane] if lane else list(signal_state.keys())

    return {
        "status": "success",
        "message": f"Adaptive control enabled for {', '.join(lanes)}",
        "timestamp": datetime.now().isoformat()
    }


# ===================== Violations Endpoints =====================


@app.get("/api/violations", response_model=List[ViolationRecord])
async def get_violations(
    lane: Optional[str] = None,
    violation_type: Optional[str] = None,
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get traffic violations.

    Query Parameters:
    - lane: Optional lane filter
    - violation_type: Optional violation type filter (red_light, speeding, etc.)
    - hours: Hours to look back (default: 24, max: 168)
    - limit: Maximum number of records (default: 100, max: 1000)

    Returns:
    - List of violation records
    """
    violations = []

    violation_types = ['red_light', 'speeding', 'illegal_turn'] if not violation_type else [violation_type]
    lanes = [lane] if lane else list(traffic_state.keys())
    severities = ['low', 'medium', 'high', 'critical']

    for i in range(min(limit, 50)):
        violations.append(
            ViolationRecord(
                violation_id=f"v_{datetime.now().timestamp()}_{i}",
                timestamp=(
                    datetime.now() - timedelta(minutes=np.random.randint(0, hours*60))
                ).isoformat(),
                lane=np.random.choice(lanes),
                vehicle_class=np.random.choice(['car', 'truck', 'motorcycle']),
                violation_type=np.random.choice(violation_types),
                severity=np.random.choice(severities),
                speed=np.random.uniform(20, 80),
                position=[np.random.uniform(-640, 640), np.random.uniform(-480, 480)]
            )
        )

    return sorted(violations, key=lambda x: x.timestamp, reverse=True)


@app.get("/api/violations/summary")
async def get_violations_summary(days: int = Query(7, ge=1, le=30)):
    """
    Get violations summary.

    Query Parameters:
    - days: Number of days to analyze

    Returns:
    - Violation summary statistics
    """
    return {
        "period_days": days,
        "total_violations": np.random.randint(50, 300),
        "by_type": {
            "red_light": np.random.randint(20, 100),
            "speeding": np.random.randint(15, 80),
            "illegal_turn": np.random.randint(5, 40)
        },
        "by_severity": {
            "low": np.random.randint(20, 60),
            "medium": np.random.randint(20, 80),
            "high": np.random.randint(10, 50),
            "critical": np.random.randint(0, 10)
        },
        "by_lane": {
            lane: np.random.randint(5, 50)
            for lane in traffic_state.keys()
        }
    }


# ===================== Export Endpoints =====================


@app.post("/api/export/daily-report")
async def export_daily_report(date: Optional[str] = None):
    """
    Generate and export daily report.

    Query Parameters:
    - date: Date for report (YYYY-MM-DD). Defaults to today.

    Returns:
    - Report as JSON
    """
    target_date = date or datetime.now().date().isoformat()

    report = {
        "report_type": "daily",
        "date": target_date,
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_vehicles": np.random.randint(5000, 15000),
            "avg_wait_time": np.random.uniform(30, 120),
            "total_violations": np.random.randint(20, 100),
            "peak_hours": [8, 9, 17, 18, 19]
        },
        "lanes": {
            lane: {
                "vehicles": np.random.randint(1000, 4000),
                "violations": np.random.randint(2, 15),
                "avg_wait_time": np.random.uniform(25, 100)
            }
            for lane in traffic_state.keys()
        }
    }

    return report


@app.post("/api/export/weekly-report")
async def export_weekly_report():
    """Generate weekly report."""
    report = {
        "report_type": "weekly",
        "week_starting": (datetime.now() - timedelta(days=datetime.now().weekday())).date().isoformat(),
        "generated_at": datetime.now().isoformat(),
        "daily_summaries": [
            {
                "date": (datetime.now() - timedelta(days=i)).date().isoformat(),
                "total_vehicles": np.random.randint(5000, 15000),
                "total_violations": np.random.randint(10, 50)
            }
            for i in range(7)
        ]
    }

    return report


# ===================== Advanced Analytics =====================


@app.get("/api/analytics/comparison")
async def compare_periods(
    start_date: str = Query("2026-03-01"),
    end_date: str = Query("2026-04-02")
):
    """
    Compare traffic metrics between two periods.

    Query Parameters:
    - start_date: Start date (YYYY-MM-DD)
    - end_date: End date (YYYY-MM-DD)

    Returns:
    - Comparison statistics
    """
    return {
        "periods": {
            "start": start_date,
            "end": end_date
        },
        "comparison": {
            "period_1": {
                "total_vehicles": np.random.randint(50000, 100000),
                "avg_wait_time": np.random.uniform(40, 120),
                "violation_rate": np.random.uniform(0.05, 0.15)
            },
            "period_2": {
                "total_vehicles": np.random.randint(50000, 100000),
                "avg_wait_time": np.random.uniform(40, 120),
                "violation_rate": np.random.uniform(0.05, 0.15)
            }
        },
        "trends": {
            "vehicle_change": f"{np.random.uniform(-10, 10):.1f}%",
            "wait_time_change": f"{np.random.uniform(-20, 20):.1f}%",
            "violation_change": f"{np.random.uniform(-30, 30):.1f}%"
        }
    }


# ===================== Startup Events =====================


@app.on_event("startup")
async def startup_event():
    """Initialize background tasks on startup."""
    logger.info("Starting Smart Traffic Management API")
    # In production, start simulation task
    # asyncio.create_task(simulate_traffic_updates())


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    logger.info("Shutting down Smart Traffic Management API")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
