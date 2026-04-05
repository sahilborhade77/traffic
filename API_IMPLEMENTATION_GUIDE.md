# API Implementation Guide

This guide covers how to implement, test, and deploy the Traffic Management System API.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Running the API](#running-the-api)
4. [Testing](#testing)
5. [Integration with Core Modules](#integration-with-core-modules)
6. [Deployment](#deployment)
7. [Monitoring & Debugging](#monitoring--debugging)
8. [Best Practices](#best-practices)

---

## Quick Start

### 1. Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt

# Verify FastAPI installation
python -c "import fastapi; print(f'FastAPI {fastapi.__version__}')"
```

### 2. Run the API Server

```bash
# Development mode (with auto-reload)
python -m uvicorn src.dashboard.api_app:app --reload --host 0.0.0.0 --port 8000

# Production mode
python -m uvicorn src.dashboard.api_app:app --host 0.0.0.0 --port 8000 --workers 4
```

### 3. Access Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## Installation

### Environment Setup

#### 1. Create Virtual Environment

```bash
# Using venv
python -m venv venv

# Or using conda
conda create -n traffic-api python=3.10
conda activate traffic-api
```

#### 2. Install Requirements

```bash
# Install all dependencies
pip install -r requirements.txt

# Install specific FastAPI dependencies
pip install fastapi==0.110.0 uvicorn==0.27.1 pydantic==2.6.0
```

#### 3. Configuration

Create a `.env` file in the project root:

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_RELOAD=false

# Database
DATABASE_URL=sqlite:///./test.db
DATABASE_ECHO=false

# Logging
LOG_LEVEL=INFO
LOG_FILE=api.log

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Feature Flags
ENABLE_WEBHOOKS=true
ENABLE_WEBSOCKET=true
ENABLE_AUTH=false
```

---

## Running the API

### Development Server

```bash
# Auto-reload on file changes
python -m uvicorn src.dashboard.api_app:app --reload \
  --host 0.0.0.0 --port 8000

# With environment variables
python -m uvicorn src.dashboard.api_app:app --reload \
  --env-file .env
```

### Production Server

```bash
# Using Gunicorn with Uvicorn workers
pip install gunicorn

gunicorn src.dashboard.api_app:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --log-level info

# Using Uvicorn directly
python -m uvicorn src.dashboard.api_app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --loop uvloop
```

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "-m", "uvicorn", "src.dashboard.api_app:app", \
     "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
# Build image
docker build -t traffic-api:latest .

# Run container
docker run -p 8000:8000 traffic-api:latest

# Run with environment file
docker run -p 8000:8000 --env-file .env traffic-api:latest
```

---

## Testing

### Unit Tests

Create `tests/test_api.py`:

```python
import pytest
from fastapi.testclient import TestClient
from src.dashboard.api_app import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_get_signals():
    response = client.get("/signals")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_list_detections():
    response = client.get("/detections?page=1&page_size=50")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data

def test_detection_not_found():
    response = client.get("/detections/99999")
    assert response.status_code == 404

def test_signal_control():
    response = client.post(
        "/signals/North/control?state=green&duration=45",
        headers={"X-Admin-Token": "test-token"}
    )
    assert response.status_code == 200
```

### Run Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_api.py -v

# Run specific test
pytest tests/test_api.py::test_health_check -v
```

### Integration Tests

```python
import pytest
import httpx

@pytest.mark.asyncio
async def test_api_integration():
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Test health
        resp = await client.get("/health")
        assert resp.status_code == 200
        
        # Test detections
        resp = await client.get("/detections")
        assert resp.status_code == 200
```

### Load Testing

Using `locust`:

```bash
pip install locust

# Create locustfile.py
cat > locustfile.py << 'EOF'
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def health_check(self):
        self.client.get("/health")
    
    @task
    def list_detections(self):
        self.client.get("/detections")
    
    @task
    def get_signals(self):
        self.client.get("/signals")
EOF

# Run load test
locust -f locustfile.py --host http://localhost:8000
```

---

## Integration with Core Modules

### Connecting to Vision Module

```python
# src/dashboard/api_app.py

from src.vision.detector import Detector

# Initialize detector
detector = Detector(model_path="yolov8n.pt")

@app.get("/detections")
def list_detections():
    # Get detections from vision module
    detections = detector.get_detections()
    return {
        "items": detections,
        "total": len(detections)
    }
```

### Connecting to Control Module

```python
from src.control.controller import TrafficController

controller = TrafficController()

@app.post("/signals/{lane}/control")
def control_signal(lane: str, state: str, duration: int):
    # Update signal through control module
    result = controller.set_signal(lane, state, duration)
    return {"success": result}
```

### Connecting to Prediction Module

```python
from src.prediction.forecaster import TrafficForecaster

forecaster = TrafficForecaster()

@app.get("/analytics/forecast/{lane}")
def get_forecast(lane: str, hours: int = 24):
    # Get predictions from forecaster
    forecast = forecaster.predict(lane, hours)
    return forecast
```

### Connecting to Analytics Module

```python
from src.analytics.analyzer import TrafficAnalyzer

analyzer = TrafficAnalyzer()

@app.get("/metrics/{lane}")
def get_lane_metrics(lane: str):
    # Get metrics from analyzer
    metrics = analyzer.get_metrics(lane)
    return metrics
```

---

## Deployment

### AWS EC2 Deployment

```bash
# Connect to instance
ssh -i key.pem ubuntu@ec2-instance

# Install Python and dependencies
sudo apt update
sudo apt install python3.10 python3-pip

# Clone repository
git clone https://github.com/org/traffic-system.git
cd traffic-system

# Install requirements
pip install -r requirements.txt

# Run with systemd
sudo tee /etc/systemd/system/traffic-api.service << EOF
[Unit]
Description=Traffic Management API
After=network.target

[Service]
Type=notify
User=ubuntu
WorkingDirectory=/home/ubuntu/traffic-system
ExecStart=/usr/bin/python3 -m uvicorn src.dashboard.api_app:app --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable traffic-api
sudo systemctl start traffic-api
sudo systemctl status traffic-api
```

### Kubernetes Deployment

Create `k8s-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: traffic-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: traffic-api
  template:
    metadata:
      labels:
        app: traffic-api
    spec:
      containers:
      - name: api
        image: traffic-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: API_PORT
          value: "8000"
        - name: LOG_LEVEL
          value: "INFO"
        livenessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
---
apiVersion: v1
kind: Service
metadata:
  name: traffic-api-service
spec:
  selector:
    app: traffic-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

Deploy:

```bash
kubectl apply -f k8s-deployment.yaml
kubectl get pods
kubectl logs deployment/traffic-api
```

---

## Monitoring & Debugging

### Prometheus Metrics

```python
# src/dashboard/api_app.py

from prometheus_client import Counter, Histogram, generate_latest

request_count = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint'])
request_duration = Histogram('api_request_duration_seconds', 'Request duration', ['endpoint'])

@app.middleware("http")
async def add_metrics(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    request_count.labels(method=request.method, endpoint=request.url.path).inc()
    request_duration.labels(endpoint=request.url.path).observe(duration)
    
    return response

@app.get("/metrics")
def metrics():
    return generate_latest()
```

### Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.get("/health")
def health_check():
    logger.info("Health check requested")
    return {"status": "healthy"}
```

### Error Tracking

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn="https://key@sentry.io/project",
    integrations=[FastApiIntegration()]
)

@app.get("/test-error")
def test_error():
    raise Exception("Test error for Sentry")
```

### Performance Debugging

```bash
# Profile API performance
pip install py-spy

# Run with profiler
py-spy record -o profile.svg -- python -m uvicorn src.dashboard.api_app:app

# Analyze with flame graph
open profile.svg
```

---

## Best Practices

### 1. Error Handling

```python
from fastapi import HTTPException

@app.get("/signals/{lane}")
def get_signal(lane: str):
    if lane not in ["North", "South", "East", "West"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid lane: {lane}"
        )
    return {"lane": lane, "state": "green"}
```

### 2. Request Validation

```python
from pydantic import BaseModel, Field

class SignalControl(BaseModel):
    state: str = Field(..., pattern="^(green|yellow|red)$")
    duration: int = Field(..., gt=0, le=300)
    
    class Config:
        example = {
            "state": "green",
            "duration": 45
        }

@app.post("/signals/{lane}/control")
def control_signal(lane: str, control: SignalControl):
    # Validated request
    return {"success": True}
```

### 3. Pagination

```python
from typing import Optional

@app.get("/detections")
def list_detections(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500)
):
    offset = (page - 1) * page_size
    # Fetch data with limit and offset
    return {"items": [...], "page": page, "page_size": page_size}
```

### 4. Caching

```python
from fastapi_cache2 import FastAPICache2
from fastapi_cache2.backends.redis import RedisBackend

@app.get("/signals")
@cached(namespace="signals", expire=60)  # Cache for 60 seconds
def get_all_signals():
    return [...]
```

### 5. Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/detections")
@limiter.limit("100/minute")
def list_detections(request: Request):
    return [...]
```

### 6. CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 7. Security Headers

```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["example.com"])

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

---

## Troubleshooting

### API Won't Start

```bash
# Check port is available
lsof -i :8000

# Check for syntax errors
python -m py_compile src/dashboard/api_app.py

# Check dependencies
pip list | grep fastapi
```

### Slow Response Times

```python
# Add timing middleware
import time

@app.middleware("http")
async def add_timing(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    response.headers["X-Process-Time"] = str(duration)
    logger.warning(f"Slow request: {request.url.path} took {duration}s")
    return response
```

### Database Connection Issues

```python
# Test database connectivity
from sqlalchemy import create_engine

engine = create_engine("sqlite:///test.db")
connection = engine.connect()
connection.execute("SELECT 1")
print("Database connection successful")
```

---

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [OpenAPI Specification](https://www.openapis.org/)

