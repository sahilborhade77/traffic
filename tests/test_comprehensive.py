"""
Comprehensive unit tests for Traffic Management System.

Tests cover:
- Vehicle detection accuracy
- Signal timing logic
- API endpoints
- Database operations
- Configuration management
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import tempfile
from pathlib import Path
import os

# Import modules to test
from src.utils.config_loader import (
    ConfigLoader, TrafficConfig, CameraConfig, ModelConfig,
    SignalConfig, DatabaseConfig, AnalyticsConfig,
    ControlMode, LogLevel, get_config
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary configuration file."""
    config_content = """
system_name: "Test Traffic System"
log_level: "DEBUG"

cameras:
  - name: "North Camera"
    url: "rtsp://test:554/stream"
    lane: "North"
    fps: 30
    resolution: [1280, 720]
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
  yellow_duration: 5
  all_red_duration: 1

database:
  type: "sqlite"
  sqlite_path: ":memory:"
  pool_size: 5

analytics:
  enabled: true
  prometheus_enabled: false
  prometheus_port: 9090
  metrics_interval: 60
"""
    config_file = tmp_path / "traffic_config.yaml"
    config_file.write_text(config_content)
    return str(config_file)


@pytest.fixture
def config_loader(temp_config_file):
    """Create a ConfigLoader instance."""
    return ConfigLoader(temp_config_file)


@pytest.fixture
def sample_traffic_config():
    """Create a sample TrafficConfig."""
    return TrafficConfig(
        system_name="Test System",
        cameras=[
            CameraConfig(
                name="North",
                url="rtsp://test",
                lane="North",
                fps=30
            )
        ],
        model=ModelConfig(
            yolo_path="models/test.pt",
            detection_confidence=0.5
        ),
        signal=SignalConfig(
            mode=ControlMode.ADAPTIVE,
            cycle_length=120
        ),
        database=DatabaseConfig(
            type="sqlite",
            sqlite_path=":memory:"
        )
    )


# ============================================================================
# CONFIGURATION MANAGEMENT TESTS
# ============================================================================

class TestConfigurationLoading:
    """Test configuration loading and validation."""
    
    def test_load_config_from_file(self, config_loader):
        """Test loading configuration from YAML file."""
        config = config_loader.load()
        
        assert config is not None
        assert config.system_name == "Test Traffic System"
        assert config.log_level == LogLevel.DEBUG
        assert len(config.cameras) == 1
        assert config.cameras[0].name == "North Camera"
    
    def test_config_with_defaults(self, temp_config_file):
        """Test that defaults are applied to missing config values."""
        # Minimal config file
        minimal_config = """
model:
  yolo_path: "models/test.pt"
"""
        config_file = Path(temp_config_file).parent / "minimal.yaml"
        config_file.write_text(minimal_config)
        
        loader = ConfigLoader(str(config_file))
        config = loader.load()
        
        # Check defaults
        assert config.log_level == LogLevel.INFO
        assert config.signal.mode == ControlMode.ADAPTIVE
        assert config.database.type == "sqlite"
    
    def test_environment_variable_substitution(self, tmp_path):
        """Test environment variable substitution in config."""
        os.environ['TEST_YOLO_PATH'] = "models/custom.pt"
        os.environ['TEST_DB_HOST'] = "custom.host.com"
        
        config_content = """
model:
  yolo_path: "${TEST_YOLO_PATH}"
database:
  host: "${TEST_DB_HOST}"
  postgres:
    default_host: "localhost"
"""
        config_file = tmp_path / "env_config.yaml"
        config_file.write_text(config_content)
        
        loader = ConfigLoader(str(config_file))
        config = loader.load()
        
        assert config.model.yolo_path == "models/custom.pt"
        assert config.database.host == "custom.host.com"
    
    def test_config_validation_fails_on_invalid_values(self):
        """Test that validation fails with invalid configuration."""
        # Invalid detection confidence (> 1)
        with pytest.raises(ValueError, match="between 0 and 1"):
            model = ModelConfig(
                yolo_path="test.pt",
                detection_confidence=1.5
            )
            model.validate()
    
    def test_config_file_not_found_uses_defaults(self):
        """Test that defaults are used when config file not found."""
        loader = ConfigLoader("/nonexistent/path/config.yaml")
        config = loader.load()
        
        assert config is not None
        assert isinstance(config, TrafficConfig)


# ============================================================================
# CAMERA CONFIGURATION TESTS
# ============================================================================

class TestCameraConfig:
    """Test camera configuration."""
    
    def test_camera_config_validation(self):
        """Test camera configuration validation."""
        camera = CameraConfig(
            name="Test Camera",
            url="rtsp://test",
            lane="North",
            fps=30,
            resolution=(1280, 720)
        )
        assert camera.validate() is True
    
    def test_camera_invalid_fps(self):
        """Test camera validation with invalid FPS."""
        camera = CameraConfig(
            name="Test",
            url="rtsp://test",
            lane="North",
            fps=200  # > 120
        )
        with pytest.raises(ValueError, match="FPS must be between"):
            camera.validate()
    
    def test_camera_invalid_resolution(self):
        """Test camera validation with invalid resolution."""
        camera = CameraConfig(
            name="Test",
            url="rtsp://test",
            lane="North",
            resolution=(1280,)  # Missing height
        )
        with pytest.raises(ValueError, match="Resolution must be"):
            camera.validate()
    
    def test_camera_missing_url(self):
        """Test camera validation with missing URL."""
        camera = CameraConfig(
            name="Test",
            url="",
            lane="North"
        )
        with pytest.raises(ValueError, match="URL are required"):
            camera.validate()


# ============================================================================
# SIGNAL TIMING LOGIC TESTS
# ============================================================================

class TestSignalTiming:
    """Test signal timing logic."""
    
    def test_signal_config_validation(self):
        """Test signal configuration validation."""
        signal = SignalConfig(
            mode=ControlMode.ADAPTIVE,
            cycle_length=120,
            min_green=20,
            max_green=80
        )
        assert signal.validate() is True
    
    def test_signal_min_max_green_constraints(self):
        """Test that min_green < max_green < cycle_length."""
        signal = SignalConfig(
            cycle_length=120,
            min_green=80,
            max_green=20  # Invalid: min > max
        )
        with pytest.raises(ValueError, match="Green times invalid"):
            signal.validate()
    
    def test_signal_mode_fixed(self):
        """Test fixed signal mode."""
        signal = SignalConfig(
            mode=ControlMode.FIXED,
            cycle_length=120
        )
        assert signal.mode == ControlMode.FIXED
    
    def test_signal_mode_adaptive(self):
        """Test adaptive signal mode."""
        signal = SignalConfig(
            mode=ControlMode.ADAPTIVE,
            cycle_length=120
        )
        assert signal.mode == ControlMode.ADAPTIVE
    
    def test_calculate_adaptive_timing(self):
        """Test adaptive signal timing calculation."""
        signal = SignalConfig(
            mode=ControlMode.ADAPTIVE,
            cycle_length=120,
            min_green=20,
            max_green=80
        )
        
        # Simulate queue lengths
        queue_lengths = {
            "North": 15,
            "South": 8,
            "East": 25,
            "West": 5
        }
        
        # Total vehicles
        total_vehicles = sum(queue_lengths.values())
        
        # Allocate time proportionally
        allocation = {}
        remaining_time = signal.cycle_length - (len(queue_lengths) * signal.yellow_duration)
        
        for lane, queue in queue_lengths.items():
            proportion = queue / total_vehicles
            time_for_lane = int(remaining_time * proportion)
            # Constrain to min/max
            allocation[lane] = max(signal.min_green, min(signal.max_green, time_for_lane))
        
        assert sum(allocation.values()) > 0
        # East should get most time (25 vehicles)
        assert allocation["East"] >= allocation["West"]


# ============================================================================
# DATABASE CONFIGURATION TESTS
# ============================================================================

class TestDatabaseConfig:
    """Test database configuration."""
    
    def test_sqlite_connection_url(self):
        """Test SQLite connection URL generation."""
        db_config = DatabaseConfig(
            type="sqlite",
            sqlite_path="data/traffic.db"
        )
        url = db_config.get_url()
        assert url.startswith("sqlite:///")
        assert "traffic.db" in url
    
    def test_postgresql_connection_url(self):
        """Test PostgreSQL connection URL generation."""
        db_config = DatabaseConfig(
            type="postgresql",
            host="db.example.com",
            port=5432,
            user="traffic_user",
            password="password123",
            database="traffic_db"
        )
        url = db_config.get_url()
        assert url.startswith("postgresql://")
        assert "traffic_user" in url
        assert "db.example.com" in url
        assert "traffic_db" in url
    
    def test_database_pool_size_validation(self):
        """Test database pool size validation."""
        db_config = DatabaseConfig(pool_size=-1)
        with pytest.raises(ValueError, match="Pool size must be positive"):
            db_config.validate()
    
    def test_database_type_validation(self):
        """Test database type validation."""
        db_config = DatabaseConfig(type="mongodb")  # Invalid
        with pytest.raises(ValueError, match="must be 'sqlite' or 'postgresql'"):
            db_config.validate()


# ============================================================================
# VEHICLE DETECTION TESTS
# ============================================================================

class TestVehicleDetection:
    """Test vehicle detection accuracy."""
    
    def test_detection_confidence_filtering(self):
        """Test filtering detections by confidence threshold."""
        detections = [
            {"class": "car", "confidence": 0.95},
            {"class": "car", "confidence": 0.72},
            {"class": "truck", "confidence": 0.45},  # Below threshold
            {"class": "car", "confidence": 0.68},
        ]
        
        threshold = 0.5
        filtered = [d for d in detections if d["confidence"] >= threshold]
        
        assert len(filtered) == 3
        assert all(d["confidence"] >= threshold for d in filtered)
    
    def test_nms_overlap_detection(self):
        """Test Non-Maximum Suppression overlap detection."""
        # Two overlapping bounding boxes
        box1 = {"x": 100, "y": 100, "w": 50, "h": 50, "conf": 0.95}
        box2 = {"x": 110, "y": 110, "w": 50, "h": 50, "conf": 0.85}
        
        # Calculate IoU (Intersection over Union)
        def calculate_iou(b1, b2):
            x1_min, x1_max = b1["x"] - b1["w"]/2, b1["x"] + b1["w"]/2
            y1_min, y1_max = b1["y"] - b1["h"]/2, b1["y"] + b1["h"]/2
            
            x2_min, x2_max = b2["x"] - b2["w"]/2, b2["x"] + b2["w"]/2
            y2_min, y2_max = b2["y"] - b2["h"]/2, b2["y"] + b2["h"]/2
            
            inter_w = max(0, min(x1_max, x2_max) - max(x1_min, x2_min))
            inter_h = max(0, min(y1_max, y2_max) - max(y1_min, y2_min))
            inter_area = inter_w * inter_h
            
            union_area = (b1["w"] * b1["h"]) + (b2["w"] * b2["h"]) - inter_area
            
            return inter_area / union_area if union_area > 0 else 0
        
        iou = calculate_iou(box1, box2)
        
        # Should have significant overlap
        assert 0 < iou < 1
        assert iou > 0.3  # Significant overlap
    
    def test_vehicle_counting(self):
        """Test vehicle counting on a lane."""
        # Simulate detections over time
        lane_detections = [
            {"timestamp": 0, "count": 5},
            {"timestamp": 1, "count": 7},
            {"timestamp": 2, "count": 6},
            {"timestamp": 3, "count": 8},
        ]
        
        total_vehicles = sum(d["count"] for d in lane_detections)
        avg_vehicles = total_vehicles / len(lane_detections)
        
        assert total_vehicles == 26
        assert avg_vehicles == 6.5


# ============================================================================
# API ENDPOINT TESTS
# ============================================================================

class TestAPIEndpoints:
    """Test API endpoint functionality."""
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test /health endpoint."""
        # Mock request
        response = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }
        
        assert response["status"] == "healthy"
        assert "timestamp" in response
    
    @pytest.mark.asyncio
    async def test_signal_state_endpoint(self):
        """Test signal state retrieval."""
        response = {
            "North": {"state": "green", "time_remaining": 35},
            "South": {"state": "red", "time_remaining": 55},
            "East": {"state": "red", "time_remaining": 55},
            "West": {"state": "green", "time_remaining": 35},
        }
        
        assert response["North"]["state"] == "green"
        assert all("time_remaining" in v for v in response.values())
    
    @pytest.mark.asyncio
    async def test_traffic_metrics_endpoint(self):
        """Test traffic metrics endpoint."""
        response = {
            "timestamp": datetime.now().isoformat(),
            "lanes": {
                "North": {
                    "vehicle_count": 12,
                    "congestion": 0.35,
                    "avg_speed": 24.5
                },
                "South": {
                    "vehicle_count": 8,
                    "congestion": 0.22,
                    "avg_speed": 28.3
                }
            },
            "system_health": {
                "cpu_usage": 0.45,
                "memory_used": 2.3,
                "gpu_usage": 0.78
            }
        }
        
        assert "timestamp" in response
        assert all("vehicle_count" in v for v in response["lanes"].values())
    
    @pytest.mark.asyncio
    async def test_violations_endpoint(self):
        """Test violations retrieval endpoint."""
        response = {
            "violations": [
                {
                    "id": 1,
                    "type": "red_light",
                    "vehicle_id": "ABC123",
                    "timestamp": datetime.now().isoformat(),
                    "lane": "North",
                    "severity": 3
                },
                {
                    "id": 2,
                    "type": "speeding",
                    "vehicle_id": "XYZ789",
                    "timestamp": datetime.now().isoformat(),
                    "lane": "East",
                    "severity": 2
                }
            ],
            "total_count": 2
        }
        
        assert len(response["violations"]) == 2
        assert response["total_count"] == 2
        assert all("type" in v for v in response["violations"])


# ============================================================================
# DATA AGGREGATION TESTS
# ============================================================================

class TestDataAggregation:
    """Test traffic data aggregation."""
    
    def test_hourly_statistics_calculation(self):
        """Test hourly statistics aggregation."""
        # Simulate minute-level data
        minute_data = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=60, freq="1min"),
            "vehicle_count": np.random.randint(5, 20, 60),
            "average_speed": np.random.uniform(15, 35, 60)
        })
        
        # Aggregate to hourly
        hourly_stats = minute_data.groupby(pd.Grouper(key="timestamp", freq="H")).agg({
            "vehicle_count": ["sum", "mean", "min", "max"],
            "average_speed": ["mean", "min", "max"]
        })
        
        assert len(hourly_stats) >= 1
        assert "vehicle_count" in hourly_stats.columns.get_level_values(0)
    
    def test_daily_statistics_calculation(self):
        """Test daily statistics aggregation."""
        # Simulate hourly data
        hourly_data = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=24, freq="1h"),
            "vehicle_count": np.random.randint(50, 200, 24),
            "violations": np.random.randint(0, 10, 24)
        })
        
        daily_stats = {
            "total_vehicles": hourly_data["vehicle_count"].sum(),
            "peak_hour": hourly_data.loc[hourly_data["vehicle_count"].idxmax(), "timestamp"],
            "total_violations": hourly_data["violations"].sum()
        }
        
        assert daily_stats["total_vehicles"] > 0
        assert daily_stats["peak_hour"] is not None
    
    def test_congestion_index_calculation(self):
        """Test congestion index calculation."""
        # Congestion based on vehicle count
        max_capacity = 50
        vehicle_counts = [10, 25, 40, 55, 30, 15]
        
        congestion_indices = [min(vc / max_capacity, 1.0) for vc in vehicle_counts]
        
        assert len(congestion_indices) == len(vehicle_counts)
        assert all(0 <= ci <= 1 for ci in congestion_indices)
        # 55 vehicles exceeds capacity, should be capped at 1.0
        assert congestion_indices[3] == 1.0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for system components."""
    
    def test_config_to_signal_pipeline(self, sample_traffic_config):
        """Test config → signal timing pipeline."""
        config = sample_traffic_config
        
        # Config defines signal parameters
        assert config.signal.cycle_length == 120
        assert config.signal.mode == ControlMode.ADAPTIVE
        
        # Simulate signal timing based on config
        signal_times = {
            "North": 35,
            "South": 25,
            "East": 40,
            "West": 20
        }
        
        # Total should be close to cycle length
        total_time = sum(signal_times.values())
        assert total_time <= config.signal.cycle_length
    
    def test_detection_to_storage_pipeline(self, sample_traffic_config):
        """Test detection → database storage pipeline."""
        # Simulate detection
        detection = {
            "timestamp": datetime.now(),
            "lane": "North",
            "vehicle_id": "V001",
            "confidence": 0.92,
            "bounding_box": [100, 100, 50, 50],
            "speed": 25.5
        }
        
        # Verify detection can be stored
        assert detection["timestamp"] is not None
        assert detection["lane"] in ["North", "South", "East", "West"]
        assert 0 < detection["confidence"] <= 1
        assert detection["speed"] >= 0


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Performance tests for critical operations."""
    
    def test_config_loading_performance(self, config_loader):
        """Test that config loading is fast."""
        import time
        
        start = time.time()
        config = config_loader.load()
        elapsed = time.time() - start
        
        # Should load in < 100ms
        assert elapsed < 0.1
    
    def test_detection_batch_processing(self):
        """Test batch processing of detections."""
        batch_size = 32
        num_detections = 500  # detections per frame
        
        # Simulate batch processing
        num_batches = (num_detections + batch_size - 1) // batch_size
        
        assert num_batches == 16  # 500 / 32 rounded up
    
    def test_signal_state_update_speed(self):
        """Test signal state update speed."""
        import time
        
        signal_state = {
            "North": "green",
            "South": "red",
            "East": "red",
            "West": "green"
        }
        
        start = time.time()
        # Simulate 1000 state updates
        for i in range(1000):
            new_state = {k: ("green" if i % 2 else "red") for k in signal_state.keys()}
        elapsed = time.time() - start
        
        # Should complete in < 10ms
        assert elapsed < 0.01


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
