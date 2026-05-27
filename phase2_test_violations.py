import cv2
import numpy as np
import logging
from datetime import datetime
import sys
import os

# Mock classes to simulate the tracker and detections
class MockTrack:
    def __init__(self, track_id, bbox, direction_history=None):
        self.track_id = track_id
        self.bbox = bbox # [x1, y1, x2, y2]
        self.confidence = 0.9
        self.class_id = 2 # car
        self.position_history = direction_history or []
    
    def get_centroid(self):
        x1, y1, x2, y2 = self.bbox
        return (x1 + x2) / 2, (y1 + y2) / 2
    
    def get_average_direction(self):
        if len(self.position_history) < 2:
            return None
        # Simplified: just return the angle between first and last
        x1, y1, _ = self.position_history[0]
        x2, y2, _ = self.position_history[-1]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        return (angle + 360) % 360

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_success(text):
    print(f"[OK] {text}")

def print_failure(text):
    print(f"[FAIL] {text}")

def test_red_light_violation():
    print_header("TEST 2.1: Red-Light Violation Detection")
    from src.violations.red_light_detector import RedLightViolationDetector, VehicleDetection, SignalState
    
    config = {
        'stop_line_y': 300,
        'violation_threshold': 10,
        'roi_polygon': np.array([[0, 250], [640, 250], [640, 400], [0, 400]])
    }
    detector = RedLightViolationDetector(config=config)
    
    # Case 1: Vehicle crosses stop line on RED (Crossing distance > threshold)
    # Centroid at 320, Stop line at 300. Diff = 20 > 10.
    v1 = VehicleDetection(track_id=1, bbox=(100, 280, 50, 50), centroid=(125, 320), vehicle_class="car", confidence=0.9)
    res = detector.check_violation(v1, SignalState.RED, SignalState.RED)
    if res:
        print_success("Red light violation detected correctly")
    else:
        print_failure("Failed to detect red light violation")

def test_speed_violation():
    print_header("TEST 2.2: Over-Speeding Detection (Point-based)")
    from src.violations.speed_detector import SpeedDetector
    
    detector = SpeedDetector(calibration_ppm=10.0, speed_threshold_kmh=60.0)
    
    # Fast vehicle: 200 pixels in 0.5 seconds = 400 px/s = 40 m/s = 144 km/h
    # Need at least 5 points for calculate_speed in speed_detector.py
    history = [
        (100, 100, 0.0),
        (125, 125, 0.1),
        (150, 150, 0.2),
        (175, 175, 0.3),
        (200, 200, 0.4),
        (300, 300, 0.5)
    ]
    res = detector.check_violation(track_id=1, track_history=history)
    if res:
        print_success(f"Speed violation detected: {res['speed_kmh']} km/h")
    else:
        print_failure("Failed to detect speed violation")

def test_wrong_way_violation():
    print_header("TEST 2.3: Wrong-Way Driving Detection")
    from src.violations.wrong_way_detector import WrongWayDetector
    
    # Traffic expected to flow South (90 degrees)
    detector = WrongWayDetector(expected_flow_angle=90.0, tolerance_degrees=45.0, min_history=2)
    
    # Vehicle moving North (270 degrees)
    history = [
        (100, 300, 0.0),
        (100, 200, 0.5) # Moving UP (-y) which is 270 degrees
    ]
    track = MockTrack(track_id=1, bbox=[100, 200, 150, 250], direction_history=history)
    
    res = detector.check(track)
    if res:
        print_success(f"Wrong-way violation detected: {res.measured_angle} degrees")
    else:
        print_failure("Failed to detect wrong-way violation")

def test_triple_riding_violation():
    print_header("TEST: Triple Riding Detection")
    from src.violations.triple_riding_detector import TripleRidingDetector
    
    class MockTensor:
        def __init__(self, data):
            self.data = data
        def cpu(self):
            return self
        def numpy(self):
            return self.data

    class MockBox:
        def __init__(self, xyxy):
            self.xyxy = [MockTensor(np.array(xyxy))]

    class MockResults:
        def __init__(self, boxes):
            self.boxes = boxes

    class MockModelManager:
        def detect(self, frame, conf, classes):
            return MockResults([
                MockBox([105, 105, 120, 140]),
                MockBox([115, 115, 130, 150]),
                MockBox([125, 125, 140, 160])
            ])

    # Using a very low threshold because IoU is small for person in bike box
    detector = TripleRidingDetector(person_overlap_threshold=0.01, max_allowed_riders=2)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    bike_bbox = (100, 100, 200, 200)
    mm = MockModelManager()
    
    res = detector.check(frame, track_id=1, bike_bbox=bike_bbox, model_manager=mm)
    if res:
        print_success(f"Triple riding detected: {res.person_count} persons")
    else:
        print_failure("Failed to detect triple riding")

if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    try:
        test_red_light_violation()
        test_speed_violation()
        test_wrong_way_violation()
        test_triple_riding_violation()
        print_header("PHASE 2 VIOLATION TESTS COMPLETED")
    except Exception as e:
        print(f"\nFATAL ERROR during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
