import pytest
import numpy as np
import cv2
import os
from src.vision.detector import VehicleDetector
from src.vision.metrics import AdvancedTrafficMetrics
from src.prediction.alerts import CongestionDetector
from src.vision.weather import WeatherAdaptiveSystem

# --- Vision Tests ---

def test_detector_initialization():
    """Checks if YOLO loads correctly."""
    detector = VehicleDetector(model_path='yolov8n.pt')
    assert detector.model is not None
    assert detector.device in [0, 'cpu']

def test_metrics_speed_calculation():
    """Verifies physics logic for speed estimation."""
    metrics = AdvancedTrafficMetrics(fps=30)
    # Move 50 pixels in 1 second
    trajectory = [(100, 100), (150, 100)]
    speed = metrics.estimate_vehicle_speed(trajectory, 1.0)
    assert speed > 0
    assert isinstance(speed, float)

def test_metrics_queue_detection():
    """Verifies that close vehicles are grouped as a queue."""
    metrics = AdvancedTrafficMetrics()
    # Two vehicles very close together
    vehicles = [(500, 500), (500, 510)] 
    queue = metrics.calculate_queue_length(vehicles)
    assert queue['queue_count'] == 2

# --- Prediction & Alert Tests ---

def test_congestion_levels():
    """Checks if density thresholds trigger correct labels."""
    detector = CongestionDetector()
    densities = {'North': 25} # Critical is 20
    levels = detector.detect_congestion_level(densities)
    assert levels['North'] == 'CRITICAL'

def test_anomaly_zscore():
    """Checks if high deviation triggers statistical alerts."""
    detector = CongestionDetector()
    current = {'North': 50}
    stats = {'North': {'mean': 10, 'std': 2}}
    anomalies = detector.detect_anomalies(current, stats)
    assert 'North' in anomalies
    assert anomalies['North']['severity'] == 'high'

# --- Weather Adaptation Tests ---

def test_weather_detection():
    """Verifies detection of night vs clear conditions."""
    system = WeatherAdaptiveSystem()
    # Create dark frame (Night)
    dark_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    condition = system.detect_weather_conditions(dark_frame)
    assert condition == 'night'

def test_weather_clarity():
    """Checks if blurry frame triggers fog/rain detection."""
    system = WeatherAdaptiveSystem()
    # Create blurry noise (Fog)
    fog_frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    fog_frame = cv2.GaussianBlur(fog_frame, (15, 15), 0)
    condition = system.detect_weather_conditions(fog_frame)
    assert condition in ['fog', 'rain']
