# Complete Traffic Management System Integration Guide

End-to-end integration of LSTM prediction, DeepSORT tracking, and red light violation detection into a unified AI-powered traffic management platform.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    VIDEO INPUT STREAM                               │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│            YOLO OBJECT DETECTION (Real-time)                        │
│  ├─ Detects: cars, trucks, motorcycles, pedestrians                │
│  ├─ Output: Detection bboxes + confidence scores                   │
│  └─ Module: src/vision/detector.py                                │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
        ┌──────────────────┐  ┌──────────────────┐
        │  DEEPSORT        │  │  LSTM            │
        │  TRACKING        │  │  PREDICTION      │
        │                  │  │                  │
        │ ├─ Multi-object  │  │ ├─ 15-min        │
        │ │   tracking     │  │ │   forecasts    │
        │ ├─ Speed/dir     │  │ ├─ Density       │
        │ │   calculation  │  │ │   prediction   │
        │ ├─ Dwell time    │  │ └─ Pattern       │
        │ │   monitoring   │  │    recognition  │
        │ └─ Trajectory    │  │                  │
        │    analysis      │  │ Output: Traffic │
        │                  │  │   alerts for     │
        │ Output:          │  │   congestion     │
        │   Vehicle tracks │  │   risk           │
        │   with metrics   │  │                  │
        └────────┬─────────┘  └────────┬─────────┘
                 │                     │
                 │     ┌───────────────┘
                 │     │
                 ▼     ▼
        ┌──────────────────────────┐
        │  SIGNAL CONTROL          │
        │  (Traffic Controller)    │
        │                          │
        │ ├─ Current signal        │
        │ │   state (RED/GREEN)   │
        │ ├─ Phase timing          │
        │ └─ Adaptive control      │
        └────────┬─────────────────┘
                 │
                 ▼
        ┌──────────────────┐
        │  RED LIGHT       │
        │  ENFORCEMENT     │
        │                  │
        │ ├─ Zone detection│
        │ ├─ Stop-line     │
        │ │   crossing     │
        │ ├─ Snapshot      │
        │ │   capture      │
        │ ├─ Violation     │
        │ │   logging      │
        │ └─ Report gen    │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │  DATABASE &      │
        │  STORAGE         │
        │                  │
        │ ├─ Violations    │
        │ ├─ Statistics    │
        │ ├─ Trends        │
        │ └─ Analytics     │
        └──────────────────┘
```

---

## Component Details

### 1. YOLO Detection Layer

**Module**: `src/vision/detector.py`

**Purpose**: Real-time object detection

```python
from src.vision.detector import YOLODetector

detector = YOLODetector(model_size='n')  # nano, small, medium, large

for frame in video:
    detections = detector.detect(frame)
    # Returns: List of (bbox, confidence, class_id, class_name)
```

**Output Format**:
```python
[
    {
        'bbox': [x1, y1, x2, y2],
        'confidence': 0.95,
        'class_id': 2,
        'class_name': 'car'
    },
    ...
]
```

---

### 2. DeepSORT Tracking Layer

**Module**: `src/vision/deepsort_tracker.py` + `src/vision/tracking_integration.py`

**Purpose**: Multi-vehicle tracking with motion metrics

```python
from src.vision.deepsort_tracker import DeepSORTTracker
from src.vision.tracking_integration import VehicleTrackingSystem

tracker = DeepSORTTracker(fps=30.0)
tracking_system = VehicleTrackingSystem(fps=30.0)

for frame in video:
    detections = detector.detect(frame)
    
    # Update tracker
    active_tracks = tracker.update(detections, frame)
    
    # Analyze tracks
    results = tracking_system.process_frame(
        frame=frame,
        detections=detections,
        frame_number=frame_count
    )
    
    # Access track data
    for track_id, track in active_tracks.items():
        print(f"Vehicle {track_id}:")
        print(f"  - Speed: {track.speed:.2f} m/s")
        print(f"  - Direction: {track.direction:.1f}°")
        print(f"  - Position: {track.position}")
```

**Active Track Structure**:
```python
{
    track_id (int): VehicleTrack {
        'track_id': int,
        'class_id': int,
        'class_name': str,
        'bbox': [x1, y1, x2, y2],
        'position': (x, y),
        'position_history': [(x, y, t), ...],
        'speed': float,  # m/s
        'direction': float,  # degrees
        'dwell_time': float,  # seconds
        'frames_tracked': int
    }
}
```

---

### 3. LSTM Prediction Layer

**Module**: `src/prediction/forecaster.py` + `src/prediction/traffic_density_predictor.py`

**Purpose**: 15-minute traffic density forecasting

```python
from src.prediction.forecaster import TrafficForecaster

forecaster = TrafficForecaster(model_path='models/traffic_lstm.pth')

# Current density from vision analysis
current_density = len(active_tracks) / zone_area

# Predict next 15 minutes
prediction = forecaster.predict_next_15_minutes(
    current_density=current_density,
    time_window=15  # minutes
)

print(f"Predicted density in 15 min: {prediction['density']:.2%}")
print(f"Confidence: {prediction['confidence']:.2%}")

# Risk assessment
if prediction['density'] > 0.75:
    print("⚠️  CONGESTION ALERT: High density predicted")
```

**Prediction Output**:
```python
{
    'density': float,  # 0.0-1.0
    'confidence': float,
    'time_horizon': int,  # minutes
    'trend': str,  # 'increasing', 'stable', 'decreasing'
    'risk_level': str  # 'low', 'medium', 'high', 'critical'
}
```

---

### 4. Signal Control Layer

**Module**: `src/control/controller.py`

**Purpose**: Adaptive traffic signal control

```python
from src.control.controller import SignalController

controller = SignalController()

# Get current signal state
signal_state = controller.get_state()
# Returns: {'North': 'RED', 'South': 'GREEN', ...}

# Update signal based on traffic conditions
if active_tracks_north > threshold:
    controller.extend_phase('North', duration=5)  # seconds
```

**Signal State Contract**:
```python
signal_state = {
    'North': 'GREEN',   # Vehicle direction name → Signal state
    'South': 'RED',
    'East': 'YELLOW',
    'West': 'GREEN'
}
```

---

### 5. Red Light Enforcement Layer

**Module**: `src/vision/red_light_detector.py` + `src/vision/red_light_integration.py`

**Purpose**: Violation detection, logging, and enforcement

```python
from src.vision.red_light_integration import EnforcementSystem, RedLightComplianceAnalyzer

# Initialize enforcement
enforcement = EnforcementSystem(
    snapshot_dir='data/violations/snapshots',
    logs_dir='data/violations/logs'
)

# Configure intersection zones
enforcement.configure_intersection(lanes_config)

# Process each frame
results = enforcement.process_frame(
    frame=frame,
    active_tracks=active_tracks,
    signal_state=signal_state,
    frame_number=frame_count
)

# Check for violations
if results['violations_detected'] > 0:
    print(f"⚠️  {results['violations_detected']} violation(s) detected")

# Analyze compliance
analyzer = RedLightComplianceAnalyzer(enforcement)
report = analyzer.generate_compliance_report()
```

---

## Complete Integration Example

```python
#!/usr/bin/env python3
"""
Complete traffic management system integration.
Combines prediction, tracking, and enforcement.
"""

import cv2
import sys
import os
from collections import deque

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from vision.detector import YOLODetector
from vision.deepsort_tracker import DeepSORTTracker
from vision.tracking_integration import VehicleTrackingSystem, DwellTimeMonitor
from vision.red_light_integration import EnforcementSystem, RedLightComplianceAnalyzer
from prediction.forecaster import TrafficForecaster
from control.controller import SignalController


class TrafficManagementPipeline:
    """Unified traffic management system."""

    def __init__(self, video_source: str = 0, fps: float = 30.0):
        """Initialize all subsystems."""
        self.fps = fps

        # Detection
        self.detector = YOLODetector(model_size='n')

        # Tracking
        self.tracker = DeepSORTTracker(fps=fps)
        self.tracking_system = VehicleTrackingSystem(fps=fps)

        # Prediction
        self.forecaster = TrafficForecaster()

        # Control
        self.signal_controller = SignalController()

        # Enforcement
        self.enforcement = EnforcementSystem(
            enable_snapshots=True,
            enable_logging=True
        )
        self.analyzer = RedLightComplianceAnalyzer(self.enforcement)

        # Dwell time monitoring
        self.dwell_monitor = DwellTimeMonitor()

        # Configure enforcement
        self._configure_intersection()

        # Metrics
        self.frame_count = 0
        self.detection_times = deque(maxlen=100)
        self.tracking_times = deque(maxlen=100)
        self.prediction_times = deque(maxlen=100)
        self.enforcement_times = deque(maxlen=100)

    def _configure_intersection(self):
        """Configure intersection for enforcement."""
        # Define lanes with zones and stop lines
        import numpy as np

        h, w = 480, 640

        lanes = {
            'North': {
                'zone': np.array([
                    [w // 2 - 40, 0],
                    [w // 2 + 40, 0],
                    [w // 2 + 40, h // 2 - 60],
                    [w // 2 - 40, h // 2 - 60]
                ], dtype=np.float32),
                'stop_line': ((w // 2 - 40, h // 2 - 60), (w // 2 + 40, h // 2 - 60)),
                'position': (w // 2, h // 4)
            },
            'South': {
                'zone': np.array([
                    [w // 2 - 40, h // 2 + 60],
                    [w // 2 + 40, h // 2 + 60],
                    [w // 2 + 40, h],
                    [w // 2 - 40, h]
                ], dtype=np.float32),
                'stop_line': ((w // 2 - 40, h // 2 + 60), (w // 2 + 40, h // 2 + 60)),
                'position': (w // 2, 3 * h // 4)
            }
        }

        self.enforcement.configure_intersection(lanes)

    def process_frame(self, frame):
        """
        Process single frame through entire pipeline.

        Returns:
            Annotated frame with all detections/tracking/violations
        """
        import time

        self.frame_count += 1
        h, w = frame.shape[:2]

        # 1. DETECTION
        t0 = time.time()
        detections = self.detector.detect(frame)
        self.detection_times.append(time.time() - t0)

        # 2. TRACKING
        t0 = time.time()
        active_tracks = self.tracker.update(detections, frame)
        tracking_results = self.tracking_system.process_frame(
            frame=frame,
            detections=detections,
            frame_number=self.frame_count
        )
        self.tracking_times.append(time.time() - t0)

        # 3. DWELL TIME MONITORING
        dwell_zones = {}  # Define zones for dwell monitoring
        dwell_results = self.dwell_monitor.update(active_tracks, dwell_zones)

        # 4. PREDICTION
        t0 = time.time()
        current_density = len(active_tracks) / (h * w)
        prediction = self.forecaster.predict_next_15_minutes(
            current_density=current_density
        )
        self.prediction_times.append(time.time() - t0)

        # 5. SIGNAL CONTROL
        signal_state = self.signal_controller.get_state()

        # Adaptive control
        if prediction['density'] > 0.75:
            self.signal_controller.extend_phase('North', duration=5)

        # 6. RED LIGHT ENFORCEMENT
        t0 = time.time()
        enforcement_results = self.enforcement.process_frame(
            frame=frame,
            active_tracks=active_tracks,
            signal_state=signal_state,
            frame_number=self.frame_count
        )
        self.enforcement_times.append(time.time() - t0)

        # 7. VISUALIZATION
        annotated = self._visualize_all(
            frame,
            detections,
            active_tracks,
            tracking_results,
            enforcement_results,
            prediction,
            signal_state
        )

        # 8. ALERTS
        self._generate_alerts(
            tracking_results,
            enforcement_results,
            prediction,
            dwell_results
        )

        return annotated

    def _visualize_all(self, frame, detections, tracks, tracking_results,
                       enforcement_results, prediction, signal_state):
        """Visualize all system outputs."""
        import cv2

        annotated = frame.copy()
        h, w = frame.shape[:2]

        # Draw detections
        for detection in detections:
            x1, y1, x2, y2 = map(int, detection['bbox'])
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                annotated,
                f"{detection['class_name']} {detection['confidence']:.2f}",
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (0, 255, 0),
                1
            )

        # Draw tracks
        for track_id, track in tracks.items():
            x, y = int(track.position[0]), int(track.position[1])
            cv2.circle(annotated, (x, y), 5, (255, 0, 0), -1)
            cv2.putText(
                annotated,
                f"ID:{track_id} v:{track.speed:.1f}",
                (x + 10, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (255, 0, 0),
                1
            )

        # Draw violations
        annotated = self.enforcement.visualize_violations(annotated)

        # Draw stats panel
        y_offset = 20
        stats_text = [
            f"Frame: {self.frame_count}",
            f"Vehicles: {len(tracks)}",
            f"Density: {len(tracks)/(h*w)*100:.1f}%",
            f"Predicted: {prediction['density']*100:.1f}%",
            f"Violations: {enforcement_results['total_violations']}",
            f"Det: {np.mean(self.detection_times)*1000:.1f}ms",
            f"Track: {np.mean(self.tracking_times)*1000:.1f}ms",
            f"Enforce: {np.mean(self.enforcement_times)*1000:.1f}ms",
        ]

        for text in stats_text:
            cv2.putText(
                annotated,
                text,
                (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1
            )
            y_offset += 20

        # Draw signal state
        y_offset = h - 100
        for lane, state in signal_state.items():
            color = {'GREEN': (0, 255, 0), 'RED': (0, 0, 255), 
                    'YELLOW': (0, 255, 255)}.get(state, (255, 255, 255))
            cv2.putText(
                annotated,
                f"{lane}: {state}",
                (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2
            )
            y_offset += 25

        return annotated

    def _generate_alerts(self, tracking_results, enforcement_results,
                        prediction, dwell_results):
        """Generate system alerts."""
        # Congestion alert
        if prediction['density'] > 0.75:
            print(f"🚨 CONGESTION ALERT: High density predicted")

        # Violation alert
        if enforcement_results['violations_detected'] > 0:
            print(f"⚠️  VIOLATION: {enforcement_results['violations_detected']} detections")

        # Speeding alert
        for track_id, metrics in tracking_results.get('speeding_vehicles', {}).items():
            if metrics['speed'] > 15:
                print(f"⚠️  SPEEDING: Vehicle {track_id} at {metrics['speed']:.1f} m/s")

    def run(self, video_source: str = 0, max_frames=None):
        """Run pipeline on video."""
        import numpy as np

        cap = cv2.VideoCapture(video_source
                              if isinstance(video_source, str)
                              else int(video_source))

        frame_count = 0

        while True:
            ret, frame = cap.read()

            if not ret:
                break

            frame_count += 1

            if max_frames and frame_count > max_frames:
                break

            # Process
            annotated = self.process_frame(frame)

            # Display
            cv2.imshow("Traffic Management System", annotated)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

        # Export results
        self.enforcement.export_violations()
        print(self.analyzer.generate_compliance_report())


# Usage
if __name__ == "__main__":
    import numpy as np

    pipeline = TrafficManagementPipeline(fps=30.0)
    pipeline.run(video_source=0, max_frames=500)
```

---

## Data Flow Summary

### Per-Frame Processing (30fps = 33ms deadline)

```
Frame Input (33ms deadline)
    │
    ├─→ Detection (5-10ms)
    │      └─→ YOLO inference
    │
    ├─→ Tracking (8-15ms)
    │      └─→ DeepSORT association + feature extraction
    │
    ├─→ Prediction (2-5ms)
    │      └─→ LSTM density forecast
    │
    ├─→ Control (1-3ms)
    │      └─→ Signal adaptation logic
    │
    ├─→ Enforcement (2-5ms)
    │      └─→ Violation detection + snapshot capture
    │
    └─→ Visualization (5-10ms)
           └─→ Annotate frame with all results

Total: ~25-50ms (Comfortable within 33ms budget)
```

---

## Output Artifacts

### 1. **Violation Records**
- Location: `data/violations/logs/violations.json`
- Contains: All violations with metadata, snapshots

### 2. **Vehicle Tracks**
- Location: `data/tracking/tracks.csv`
- Contains: Speed, direction, dwell time per vehicle

### 3. **Traffic Predictions**
- Location: `data/predictions/forecasts.csv`
- Contains: Density predictions over 15-minute windows

### 4. **Compliance Reports**
- Location: `data/reports/compliance_*.txt`
- Contains: Lane compliance rates, peak violation times

### 5. **System Metrics**
- Processing times per component
- Detection/tracking accuracy
- Enforcement statistics
- Traffic pattern trends

---

## Production Deployment

### System Requirements

- **GPU**: NVIDIA RTX 2050+ (or equivalent)
- **CPU**: Intel i7/Ryzen 7 minimum
- **RAM**: 16GB+ (8GB minimum)
- **Storage**: SSD 256GB+ (for violation snapshots)
- **Network**: Gigabit for alert distribution

### Configuration Files

1. **`config/camera_config.yaml`**: Camera calibration
2. **`config.yaml`**: System parameters
3. **`requirements.txt`**: Python dependencies

### Monitoring and Maintenance

```python
# Health check
system_healthy = [
    avg_detection_time < 15,      # ms
    avg_tracking_time < 20,       # ms
    avg_enforcement_time < 10,    # ms
    violation_capture_success > 0.95,  # %
    gpu_memory_available > 1.0    # GB
]

if all(system_healthy):
    print("✅ System operational")
else:
    print("⚠️  System degraded - investigate metrics")
```

---

## Integration Checklist

- [ ] All models downloaded and in `models/` directory
  - [ ] `yolov8n.pt` for detection
  - [ ] `traffic_lstm.pth` for prediction
  - [ ] `dqn_traffic.pth` for control (optional)

- [ ] Camera calibration complete
  - [ ] Intrinsic parameters in `config/camera_config.yaml`
  - [ ] Zone coordinates calibrated
  - [ ] Stop lines precisely marked

- [ ] Signal timing configured
  - [ ] Phase durations in `config.yaml`
  - [ ] Signal state mapping verified
  - [ ] Safety clearing times validated

- [ ] Storage configured
  - [ ] Violation directories exist
  - [ ] Write permissions verified
  - [ ] Retention policy set

- [ ] Testing complete
  - [ ] Unit tests passing
  - [ ] Integration tests passing
  - [ ] End-to-end validation done
  - [ ] Performance benchmarks acceptable

- [ ] Monitoring setup
  - [ ] Logging configured
  - [ ] Alerts configured
  - [ ] Database connection tested
  - [ ] Report generation verified

---

## Troubleshooting

### Low Detection Rate
- Check YOLO model file exists
- Verify camera calibration
- Check lighting conditions

### Tracking Loss
- Increase max_age parameter in DeepSORT
- Improve detection rate first
- Check frame rate consistency

### Violation False Positives
- Refine zone boundaries
- Adjust confidence thresholds
- Verify signal state timing

### Performance Issues
- Reduce detection resolution
- Use smaller YOLO model (nano)
- Disable snapshot capture if needed
- Profile with `cProfile`

---

**Next Steps:**
1. Customize zones for your intersection
2. Run test videos to validate
3. Deploy monitoring dashboard
4. Integrate with traffic database
5. Set up automatic record archival

