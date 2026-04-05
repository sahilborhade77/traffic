"""
Pytest configuration and shared fixtures for all tests.
"""

import pytest
import tempfile
from pathlib import Path
import os
from typing import Generator
import asyncio


# ============================================================================
# SESSION-LEVEL FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def temp_data_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture(scope="session")
def test_config_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test configuration."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


# ============================================================================
# FUNCTION-LEVEL FIXTURES
# ============================================================================

@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary configuration file for testing."""
    config_content = """
system_name: "Test Traffic System"
log_level: "DEBUG"

cameras:
  - name: "North Camera"
    url: "rtsp://test:554/stream"
    lane: "North"
    fps: 30
    enabled: true

  - name: "South Camera"
    url: "rtsp://test:554/stream"
    lane: "South"
    fps: 30
    enabled: true

model:
  yolo_path: "models/test.pt"
  detection_confidence: 0.5
  nms_threshold: 0.45
  device: "cpu"
  batch_size: 4

signal:
  mode: "adaptive"
  cycle_length: 120
  min_green: 20
  max_green: 80

database:
  type: "sqlite"
  sqlite_path: ":memory:"
  pool_size: 5

analytics:
  enabled: true
  prometheus_enabled: false
"""
    config_file = tmp_path / "traffic_config.yaml"
    config_file.write_text(config_content)
    return str(config_file)


@pytest.fixture
def sample_detection_data():
    """Create sample vehicle detection data."""
    return {
        "timestamp": "2024-01-01T12:00:00",
        "lane": "North",
        "vehicle_id": "V001",
        "confidence": 0.92,
        "bounding_box": [100, 100, 50, 50],
        "speed": 25.5,
        "vehicle_class": "car"
    }


@pytest.fixture
def sample_violation_data():
    """Create sample violation record data."""
    return {
        "timestamp": "2024-01-01T12:00:00",
        "lane": "North",
        "vehicle_id": "V001",
        "violation_type": "red_light",
        "severity": 3,
        "speed": 45.0
    }


@pytest.fixture
def sample_signal_state():
    """Create sample signal state data."""
    return {
        "North": {"state": "green", "time_remaining": 35},
        "South": {"state": "red", "time_remaining": 55},
        "East": {"state": "red", "time_remaining": 55},
        "West": {"state": "green", "time_remaining": 35},
    }


@pytest.fixture
def mock_camera_feed():
    """Create a mock camera feed."""
    import numpy as np
    # Mock video frame (1280x720 RGB)
    return np.zeros((720, 1280, 3), dtype=np.uint8)


@pytest.fixture
def mock_detections():
    """Create mock YOLO detections."""
    return [
        {"x": 100, "y": 100, "w": 50, "h": 50, "confidence": 0.95, "class": "car"},
        {"x": 200, "y": 150, "w": 45, "h": 45, "confidence": 0.88, "class": "truck"},
        {"x": 300, "y": 200, "w": 40, "h": 40, "confidence": 0.72, "class": "car"},
    ]


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture
def sqlite_db(tmp_path):
    """Create a temporary SQLite database for testing."""
    db_path = tmp_path / "test_traffic.db"
    db_url = f"sqlite:///{db_path}"
    return db_url


@pytest.fixture
def postgres_db():
    """PostgreSQL database connection string for testing."""
    # Note: Requires PostgreSQL service running
    db_url = "postgresql://traffic_user:traffic_pass@localhost:5432/traffic_test_db"
    return db_url


# ============================================================================
# MOCKING FIXTURES
# ============================================================================

@pytest.fixture
def mock_yolo_model():
    """Create a mock YOLO model."""
    from unittest.mock import MagicMock
    
    model = MagicMock()
    model.predict.return_value = [
        {
            "boxes": {
                "xyxy": [[100, 100, 150, 150], [200, 200, 250, 250]],
                "conf": [0.95, 0.88]
            }
        }
    ]
    return model


@pytest.fixture
def mock_database():
    """Create a mock database manager."""
    from unittest.mock import MagicMock
    
    db_manager = MagicMock()
    db_manager.add_vehicle_detection.return_value = 1
    db_manager.record_violation.return_value = 1
    db_manager.get_violations.return_value = []
    return db_manager


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    from unittest.mock import MagicMock
    
    redis_client = MagicMock()
    redis_client.get.return_value = None
    redis_client.set.return_value = True
    redis_client.delete.return_value = 1
    return redis_client


# ============================================================================
# API FIXTURES
# ============================================================================

@pytest.fixture
def api_client():
    """Create a test API client."""
    from fastapi.testclient import TestClient
    # Import your API app here
    # from src.dashboard.backend import app
    # return TestClient(app)
    
    from unittest.mock import MagicMock
    return MagicMock()


@pytest.fixture
def api_base_url():
    """Get API base URL for testing."""
    return "http://localhost:8000"


# ============================================================================
# LOGGING FIXTURES
# ============================================================================

@pytest.fixture(autouse=True)
def setup_logging(caplog):
    """Setup logging for tests."""
    caplog.set_level("DEBUG")
    return caplog


# ============================================================================
# PERFORMANCE FIXTURES
# ============================================================================

@pytest.fixture
def benchmark_timer():
    """Simple benchmark timer for tests."""
    import time
    
    class Timer:
        def __enter__(self):
            self.start = time.time()
            return self
        
        def __exit__(self, *args):
            self.elapsed = time.time() - self.start
        
        @property
        def milliseconds(self):
            return self.elapsed * 1000
    
    return Timer()


# ============================================================================
# CLEANUP and TEARDOWN
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_env_vars():
    """Clean up environment variables after each test."""
    env_backup = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(env_backup)


def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers",
        "database: marks tests that require database"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add database marker
        if "database" in item.nodeid or "db" in item.nodeid:
            item.add_marker(pytest.mark.database)
        
        # Add integration marker
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        # Add slow marker for specific tests
        if "slow" in item.nodeid:
            item.add_marker(pytest.mark.slow)


@pytest.fixture(scope="session", autouse=True)
def create_test_logs_dir():
    """Create logs directory for test output."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    return log_dir
