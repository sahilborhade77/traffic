from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
import json
import time
import cv2
import asyncio
import logging
from prometheus_client import Counter, Gauge, generate_latest
from fastapi.responses import Response
import torch
import numpy as np

# Config Logging
logger = logging.getLogger(__name__)
app = FastAPI(title="Smart AI Traffic Management Hub")

@app.get("/")
async def root():
    """Welcome endpoint for the API Hub."""
    return {
        "status": "online",
        "message": "Smart AI Traffic API Hub is alive.",
        "documentation": "/docs",
        "dashboard_ui": "Run 'streamlit run src/dashboard/app.py' to view the UI"
    }

class ConnectionManager:
    """Manages all active WebSocket connections for real-time broadcasts."""
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New client connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Active: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Sends data to all connected browsers instantly."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                continue

manager = ConnectionManager()

# --- AI Observability Metrics (Prometheus) ---
TRAFFIC_COUNT = Counter('traffic_vehicles_total', 'Total vehicles detected', ['lane', 'type'])
WAIT_TIME = Gauge('traffic_wait_time_seconds', 'Current average wait time per lane', ['lane'])
FPS_GAUGE = Gauge('traffic_ai_fps', 'Current frames per second of the Vision Engine')

@app.get("/metrics")
async def metrics_endpoint():
    """Scrape point for Prometheus & Grafana."""
    return Response(content=generate_latest(), media_type="text/plain")

# --- AI PREDICTION API ---
@app.post("/api/predict")
async def predict_traffic(history: list):
    """
    Real-time LSTM Prediction Query.
    Expects a list of 60 historic traffic density points.
    """
    try:
        # Load the LSTM Brain
        from src.prediction.lstm_model import TrafficFlowPredictor
        model = TrafficFlowPredictor() # In production, this would be a pre-loaded singleton
        
        # Prepare data for LSTM: (batch=1, seq=60, feat=4)
        input_tensor = torch.FloatTensor(np.array(history)).view(1, 60, 4)
        
        with torch.no_grad():
            predictions = model(input_tensor)
            
        return {
            'status': 'success',
            'forecast': predictions.tolist()[0],
            'confidence': 0.89, # Placeholder for model confidence logic
            'horizon_minutes': 2
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

# --- REAL-TIME ENDPOINTS ---

@app.websocket("/ws/traffic")
async def traffic_websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep-alive loop
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/analytics")
async def get_historical_analytics():
    """REST endpoint for dashboard charts."""
    # Here you would load from your data/traffic_analytics.json
    return {
        'timestamp': time.time(),
        'summary': {
            'daily_volume': 12450,
            'peak_hour': '17:30 - 18:30',
            'average_wait_time_sec': 42.5,
            'total_throughput': 850
        }
    }

# --- GLOBAL BROADCAST HELPER ---

async def broadcast_traffic_update(lane_data, congestion_level, signal_phase):
    """
    Called by the Vision/Control modules to update the Web Dashboard.
    """
    total_vehicles = sum([lane['current_density'] for lane in lane_data.values()])
    
    update = {
        'type': 'TRAFFIC_REALTIME',
        'timestamp': time.time(),
        'lanes': lane_data,
        'total_vehicles': total_vehicles,
        'congestion_level': congestion_level,
        'signal_phase_id': signal_phase
    }
    await manager.broadcast(update)

# --- VIDEO STREAMING (MJPEG) ---

def generate_video_stream():
    """Generator for streaming processed AI video to the browser."""
    # This would ideally be linked to your TrafficVideoProcessor's latest frame
    # For now, it opens the default camera (0) or a file for testing.
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Encoding for MJPEG stream
        _, jpeg = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')

@app.get("/api/video_stream")
async def video_stream_endpoint():
    """Endpoint for the browser <img src='/api/video_stream' />"""
    return StreamingResponse(generate_video_stream(), media_type="multipart/x-mixed-replace; boundary=frame")
