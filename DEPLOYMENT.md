# Deployment & Testing Guide

This guide covers the complete deployment and testing setup for the Traffic Management System.

## Table of Contents
1. [Local Development Setup](#local-development-setup)
2. [Docker Deployment](#docker-deployment)
3. [Configuration Management](#configuration-management)
4. [Testing](#testing)
5. [CI/CD Pipeline](#cicd-pipeline)
6. [Troubleshooting](#troubleshooting)

---

## Local Development Setup

### Prerequisites
- Python 3.9+
- CUDA 11.8 (for GPU support)
- Docker & Docker Compose
- Git

### Installation Steps

1. **Clone Repository**
```bash
git clone https://github.com/yourusername/traffic-project.git
cd traffic_project
```

2. **Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. **Install Dependencies**
```bash
# Production dependencies
pip install -r requirements.txt

# Development dependencies (for testing)
pip install -r requirements-dev.txt
```

4. **Set Environment Variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Run Tests Locally**
```bash
# Run all tests
pytest tests/ -v

# Run specific test category
pytest tests/ -v -m unit
pytest tests/ -v -m integration

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

---

## Docker Deployment

### Build Docker Image

```bash
# Build image locally
docker build -t traffic-management:latest .

# Build with specific tag
docker build -t traffic-management:v1.0.0 .

# Build for production (multi-stage)
docker build -t traffic-management:prod \
  --build-arg PYTHON_VERSION=3.10 \
  --target runtime .
```

### Docker Compose Deployment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Rebuild services
docker-compose up -d --build
```

### Service URLs After Deployment
- **API**: http://localhost:8000
- **Dashboard**: http://localhost:8501
- **Prometheus**: http://localhost:9091
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check service status
docker-compose ps

# View service logs
docker-compose logs traffic-api
docker-compose logs traffic-dashboard
docker-compose logs traffic-vision
```

---

## Configuration Management

### YAML Configuration File

Configuration is defined in `config/traffic_config.yaml`:

```yaml
system_name: "Traffic Management System"
log_level: "INFO"

cameras:
  - name: "North Lane Camera"
    url: "rtsp://192.168.1.100:554/stream"
    lane: "North"
    fps: 30

model:
  yolo_path: "models/yolov8n.pt"
  detection_confidence: 0.5
  device: "cuda"

signal:
  mode: "adaptive"
  cycle_length: 120
  min_green: 20
  max_green: 80

database:
  type: "postgresql"  # or "sqlite"
  host: "localhost"
  port: 5432
  database: "traffic_db"

analytics:
  enabled: true
  prometheus_enabled: true
```

### Environment Variable Substitution

Configuration supports environment variable substitution:

```yaml
model:
  yolo_path: "${YOLO_MODEL_PATH:models/yolov8n.pt}"
database:
  host: "${DB_HOST:localhost}"
```

### Loading Configuration in Code

```python
from src.utils.config_loader import load_config, get_config

# Load from file
config = load_config("config/traffic_config.yaml")

# Or use global instance
config = get_config()

# Access configuration
print(config.system_name)
print(config.signal.cycle_length)
print(config.cameras[0].url)
```

### Configuration Validation

Configurations are automatically validated:

```python
from src.utils.config_loader import TrafficConfig

config = TrafficConfig(...)
try:
    config.validate()  # Raises ValueError if invalid
except ValueError as e:
    print(f"Configuration error: {e}")
```

---

## Testing

### Unit Tests

```bash
# Run all unit tests
pytest tests/test_comprehensive.py -v -m unit

# Run specific test class
pytest tests/test_comprehensive.py::TestConfigurationLoading -v

# Run specific test function
pytest tests/test_comprehensive.py::TestConfigurationLoading::test_load_config_from_file -v
```

### Integration Tests

```bash
# Run integration tests (requires services running)
pytest tests/ -v -m integration

# Run with database
pytest tests/ -v -m database
```

### Coverage Reports

```bash
# Generate HTML coverage report
pytest tests/ --cov=src --cov-report=html

# View report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows

# Coverage in terminal
pytest tests/ --cov=src --cov-report=term-missing
```

### Test Categories

Tests are organized by:
- **unit**: Fast, isolated unit tests
- **integration**: Tests requiring multiple components
- **database**: Tests requiring database
- **slow**: Long-running tests
- **api**: API endpoint tests

```bash
# Run only fast tests
pytest tests/ -v -m "not slow"

# Run only API tests
pytest tests/ -v -m api
```

### Performance Testing

```bash
# Run performance tests
pytest tests/test_comprehensive.py::TestPerformance -v

# Run with profiling
pytest tests/ --profile
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

The project includes a comprehensive CI/CD pipeline (`.github/workflows/ci-cd.yml`) that:

1. **Tests**: Runs pytest on Python 3.9, 3.10, 3.11
2. **Linting**: Checks code quality with Flake8, Black, isort
3. **Security**: Scans with Trivy and Bandit
4. **Build**: Builds Docker image
5. **Deploy**: Deploys to staging/production

### Triggering Workflows

Workflows are triggered by:
- **Push to main/develop**: Runs all tests and builds image
- **Pull Requests**: Runs tests, linting, and security checks
- **Schedule**: Daily tests at 2 AM UTC
- **Manual**: Can trigger via GitHub UI

### Viewing Pipeline Results

1. Go to repository → Actions tab
2. Click on workflow run to see detailed logs
3. Coverage reports available in artifacts
4. Deployment status in environment tabs

### Secrets Configuration

Add these secrets in repository settings:
- `SLACK_WEBHOOK`: For notifications
- `REGISTRY_USERNAME`: Container registry credentials
- `REGISTRY_PASSWORD`: Container registry credentials

---

## Production Deployment

### Kubernetes Deployment

```yaml
# deployment.yaml
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
      - name: traffic-api
        image: ghcr.io/yourusername/traffic-project:latest
        ports:
        - containerPort: 8000
        env:
        - name: CONFIG_PATH
          value: /etc/traffic/config.yaml
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
            nvidia.com/gpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2000m"
            nvidia.com/gpu: "1"
        volumeMounts:
        - name: config
          mountPath: /etc/traffic
      volumes:
      - name: config
        configMap:
          name: traffic-config
```

### Health Checks

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 20
  periodSeconds: 5
```

---

## Troubleshooting

### Docker Issues

**Container fails to start**
```bash
# View detailed logs
docker logs container_name

# Rebuild without cache
docker-compose build --no-cache

# Check resource usage
docker stats
```

**GPU not detected**
```bash
# Inside container
nvidia-smi

# Check Docker GPU support
docker run --rm --gpus all nvidia/cuda:11.8-runtime nvidia-smi
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
psql -h localhost -U traffic_user -d traffic_db

# Check database logs
docker logs traffic-postgres

# Reset database
docker-compose down -v
docker-compose up -d postgres
```

### Configuration Problems

**Config file not found**
```python
# Explicitly set config path
import os
os.environ['CONFIG_PATH'] = '/path/to/config.yaml'

from src.utils.config_loader import get_config
config = get_config()
```

**Environment variable not substituted**
```yaml
# Ensure format is correct
url: "${ENV_VAR_NAME:default_value}"

# Check environment variables
echo $ENV_VAR_NAME
```

### Test Failures

**Timeout errors**
```bash
# Increase timeout
pytest tests/ --timeout=600

# Run without timeout
pytest tests/ -o timeout=0
```

**Database connection errors**
```bash
# Ensure PostgreSQL service is running
docker-compose up -d postgres

# Check service health
docker-compose ps
```

---

## Performance Optimization

### Docker Image Optimization

- Multi-stage builds reduce image size
- Use `.dockerignore` to exclude unnecessary files
- Pin specific package versions

### Database Optimization

- Indexes on frequently queried columns
- Connection pooling configured
- Regular table maintenance

### Application Optimization

- Configuration caching
- Batch processing for detections
- Asynchronous I/O operations

---

## Monitoring & Logging

### Prometheus Metrics

Access at: http://localhost:9091

Key metrics:
- `traffic_vehicle_count`: Total vehicles detected
- `traffic_violations_total`: Total violations
- `traffic_avg_wait_time`: Average wait time
- `traffic_detection_latency`: Detection processing time

### Application Logs

```bash
# View logs
docker-compose logs -f traffic-api

# Filter by service
docker-compose logs traffic-vision

# Follow logs in real-time
docker-compose logs -f --tail=100
```

---

## Support & Contributions

For issues and questions:
1. Check the troubleshooting section
2. Review GitHub Issues
3. Create detailed bug report with logs
4. Submit pull request for improvements

---

## License

Copyright © 2024 Traffic Management System. All rights reserved.
