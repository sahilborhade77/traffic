#!/usr/bin/env python3
"""
Phase 1: Task 1.3 - Detection & Tracking Stability Test
Tests vehicle detection and tracking module initialization and basic functionality
"""

import sys
import os
import time
import numpy as np
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}✗ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠ {text}{RESET}")

def test_detection_module():
    """Test 1.3.1: Vehicle Detection Module"""
    print_header("TEST 1.3.1: Vehicle Detection Module")
    
    try:
        print("Importing VehicleDetector...")
        from src.detection.vehicle_detector import VehicleDetector
        print_success("Import successful")
        
        print("Initializing YOLO model...")
        detector = VehicleDetector(model_path="yolov8n.pt")
        print_success("YOLO model loaded successfully")
        
        # Test with dummy frame
        print("\nTesting detection on dummy frame...")
        dummy_frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
        
        results = detector.detect(dummy_frame)
        print_success(f"Detection successful - Found {len(results) if results else 0} objects")
        
        # Print detection details
        if results:
            print(f"  - Detection classes: {[r.get('class', 'unknown') for r in results[:3]]}")
            print(f"  - Confidence scores: {[round(r.get('conf', 0), 2) for r in results[:3]]}")
        
        return True
        
    except Exception as e:
        print_error(f"Detection module test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tracking_module():
    """Test 1.3.2: Vehicle Tracking Module"""
    print_header("TEST 1.3.2: Vehicle Tracking Module")
    
    try:
        print("Importing DeepSORT tracker...")
        from src.tracking.deepsort_tracker import DeepSORTTracker as DeepSORT
        print_success("Import successful")
        
        print("Initializing DeepSORT...")
        tracker = DeepSORT(max_age=30, n_init=3)
        print_success("DeepSORT tracker initialized")
        
        # Test tracking with dummy detections
        print("\nTesting tracking with dummy detections...")
        dummy_detections = [
            ([100, 100, 50, 100], 0.9, 2),
            ([300, 150, 50, 100], 0.85, 2),
        ]
        
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        tracked_objects = tracker.update(dummy_detections, frame=dummy_frame)
        print_success(f"Tracking update successful - Tracked {len(tracked_objects)} objects")
        
        # Print tracking details
        if tracked_objects:
            for obj in tracked_objects[:3]:
                print(f"  - Track ID: {obj.get('track_id', 'unknown')}, Bbox: {obj.get('bbox', [])}")
        
        return True
        
    except Exception as e:
        print_error(f"Tracking module test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_end_to_end_pipeline():
    """Test 1.3.3: End-to-End Detection + Tracking"""
    print_header("TEST 1.3.3: End-to-End Pipeline (Detection + Tracking)")
    
    try:
        print("Loading detection and tracking modules...")
        from src.detection.vehicle_detector import VehicleDetector
        from src.tracking.deepsort_tracker import DeepSORTTracker as DeepSORT
        
        detector = VehicleDetector(model_path="yolov8n.pt")
        tracker = DeepSORT()
        print_success("Modules loaded")
        
        print("\nSimulating 10-frame processing...")
        total_detections = 0
        total_tracks = 0
        
        for frame_idx in range(10):
            # Create dummy frame
            frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
            
            # Detect
            detections = detector.detect(frame)
            
            # Track
            tracks = tracker.update(detections, frame=frame)
            
            total_detections += len(detections) if detections else 0
            total_tracks += len(tracks) if tracks else 0
            
            # Progress
            print(f"  Frame {frame_idx+1:2d}: Detected {len(detections) if detections else 0} objects, "
                  f"Tracked {len(tracks) if tracks else 0} tracks")
        
        print_success(f"Pipeline test complete")
        print(f"  - Total detections: {total_detections}")
        print(f"  - Total track updates: {total_tracks}")
        
        return True
        
    except Exception as e:
        print_error(f"End-to-end pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_connection():
    """Test database connectivity"""
    print_header("TEST: Database Connection")
    
    try:
        print("Connecting to database...")
        from src.database.violation_db import ViolationDatabase
        from src.database.models import Violation
        
        db_url = os.getenv('DATABASE_URL', 'sqlite:///traffic.db')
        db = ViolationDatabase(db_url=db_url)
        print_success(f"Database connected: {db_url}")
        
        # Test query
        print("Running test query...")
        session = db.session
        count = session.query(Violation).count()
        print_success(f"Database query successful - {count} violations in database")
        
        return True
        
    except Exception as e:
        print_error(f"Database connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoint():
    """Test API connectivity"""
    print_header("TEST: API Endpoint Connectivity")
    
    try:
        print("Testing API health endpoint...")
        import requests
        
        response = requests.get("http://localhost:8000/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"API is {data.get('status', 'unknown')}")
            print(f"  - Version: {data.get('version', 'unknown')}")
            print(f"  - Database: {data.get('database', 'unknown')}")
            return True
        else:
            print_warning(f"API returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_warning("API not running - make sure FastAPI server is started")
        print_warning("Run: .venv\\Scripts\\python -m uvicorn src.api.main_api:app --reload")
        return None
    except Exception as e:
        print_error(f"API test failed: {e}")
        return False

def main():
    """Run all Phase 1 tests"""
    print_header("PHASE 1: TASK 1.3 - Detection & Tracking Stability Tests")
    
    results = {}
    
    # Test 1: Detection Module
    results['detection'] = test_detection_module()
    time.sleep(1)
    
    # Test 2: Tracking Module
    results['tracking'] = test_tracking_module()
    time.sleep(1)
    
    # Test 3: End-to-End Pipeline
    results['pipeline'] = test_end_to_end_pipeline()
    time.sleep(1)
    
    # Test 4: Database
    results['database'] = test_database_connection()
    time.sleep(1)
    
    # Test 5: API
    results['api'] = test_api_endpoint()
    
    # Summary
    print_header("PHASE 1: TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    for test_name, result in results.items():
        if result is True:
            status = f"{GREEN}PASSED{RESET}"
        elif result is False:
            status = f"{RED}FAILED{RESET}"
        else:
            status = f"{YELLOW}SKIPPED{RESET}"
        
        print(f"  {test_name.upper():15s}: {status}")
    
    print(f"\n{GREEN}Total Passed: {passed}{RESET}")
    print(f"{RED}Total Failed: {failed}{RESET}")
    print(f"{YELLOW}Total Skipped: {skipped}{RESET}")
    
    if failed == 0:
        print(f"\n{GREEN}✓ Phase 1 Task 1.3: PASSED - Detection & Tracking Stable{RESET}")
        return 0
    else:
        print(f"\n{RED}✗ Phase 1 Task 1.3: FAILED - Fix errors above{RESET}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
