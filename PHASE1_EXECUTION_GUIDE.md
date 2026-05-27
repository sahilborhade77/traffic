# PHASE 1: CRITICAL FIXES & STABILIZATION - EXECUTION GUIDE

**Duration:** 1-2 weeks  
**Status:** 🔴 STARTING NOW  
**Priority:** P0 - CRITICAL

---

## 📋 Overview

Phase 1 consists of three critical tasks that must be completed sequentially:

1. ✅ **Task 1.1:** Fix Streamlit Dashboard Network Issues
2. ✅ **Task 1.2:** Fix Backend Service Connectivity  
3. ✅ **Task 1.3:** Stabilize Vehicle Detection & Tracking
4. ✅ **Task 1.4:** Integration Testing & Validation

---

## 🚀 GETTING STARTED

### Prerequisites
- ✅ Virtual environment activated: `.venv\Scripts\Activate.ps1`
- ✅ All dependencies installed (pip install completed)
- ✅ `.env` file created (✅ DONE - at project root)

### Files Created for Phase 1
- `/.env` - Environment configuration
- `/phase1_startup.py` - Service startup script
- `/phase1_test_detection_tracking.py` - Testing script

---

## 📝 TASK 1.1: Fix Streamlit Dashboard Network Issues

### Problem
```
Error: Cannot load Streamlit frontend code
Reason: Dashboard and backend services not connected properly
```

### ✅ Solution Steps

**Step 1.1.1: Start Backend Service (FastAPI)**

Open **Terminal 1** and run:
```bash
# Activate venv (if not already active)
.venv\Scripts\Activate.ps1

# Start FastAPI backend
python -m uvicorn src.api.main_api:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

**Step 1.1.2: Verify API Health**

Open **Terminal 2** and run:
```bash
# Test API health endpoint
curl http://localhost:8000/health

# Or use Python
python -c "import requests; print(requests.get('http://localhost:8000/health').json())"
```

Expected response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "database": "connected",
  "api": "running"
}
```

**Step 1.1.3: Start Streamlit Dashboard (FastAPI)**

Open **Terminal 3** and run:
```bash
# Activate venv
.venv\Scripts\Activate.ps1

# Start Streamlit
python -m streamlit run src/dashboard/app.py
```

Expected output:
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

**Step 1.1.4: Verify Dashboard in Browser**

1. Open: `http://localhost:8501`
2. Check that:
   - Dashboard loads without "Network issue" error
   - All sections are visible
   - Metrics display correctly

✅ **Task 1.1 Complete** when dashboard loads with no errors

---

## 🔧 TASK 1.2: Fix Backend Service Connectivity

### Problem
- Backend processes not running
- API not responding to requests
- Database not connected

### ✅ Solution Steps

**Step 1.2.1: Verify Services are Running**

```bash
# Check if backend is running (port 8000)
netstat -ano | findstr :8000

# Check if Streamlit is running (port 8501)
netstat -ano | findstr :8501

# If services not running, see Task 1.1
```

**Step 1.2.2: Test Database Connection**

In Python terminal:
```python
# Test database connectivity
from src.database.violation_db import ViolationDatabase
from src.database.models import Violation

db = ViolationDatabase(db_url='sqlite:///traffic.db')
session = db.get_session()

# Count violations
count = session.query(Violation).count()
print(f"✓ Database connected - {count} violations found")

session.close()
```

Expected output:
```
✓ Database connected - 0 violations found
(or any number of existing violations)
```

**Step 1.2.3: Test API Endpoints**

```bash
# Test root endpoint
curl http://localhost:8000/

# Test health endpoint
curl http://localhost:8000/health

# Test violations endpoint
curl http://localhost:8000/violations/recent?limit=5
```

Expected responses:
```json
{"status": "online", "system": "Traffic Intelligence System v2.0"}
{"status": "healthy", "version": "2.0.0", ...}
{"violations": [...]}
```

**Step 1.2.4: Check Environment Variables**

```bash
# Verify .env is loaded correctly
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(f'DB_URL: {os.getenv(\"DATABASE_URL\")}')"
```

Expected output:
```
DB_URL: sqlite:///traffic.db
```

✅ **Task 1.2 Complete** when all endpoints respond successfully

---

## 🎬 TASK 1.3: Stabilize Vehicle Detection & Tracking

### Problem
- Detection and tracking models not initialized
- Module import failures
- Model loading errors

### ✅ Solution Steps

**Step 1.3.1: Run Automated Tests**

```bash
# Run comprehensive test suite
python phase1_test_detection_tracking.py
```

This tests:
- ✅ Detection module initialization
- ✅ Tracking module initialization
- ✅ End-to-end pipeline (10 frames)
- ✅ Database connection
- ✅ API connectivity

Expected output:
```
============================================================================
  TEST 1.3.1: Vehicle Detection Module
============================================================================

Importing VehicleDetector...
✓ Import successful
Initializing YOLO model...
✓ YOLO model loaded successfully
...

============================================================================
PHASE 1: TEST SUMMARY
============================================================================
  DETECTION       : PASSED
  TRACKING        : PASSED
  PIPELINE        : PASSED
  DATABASE        : PASSED
  API             : PASSED

Total Passed: 5
Total Failed: 0
Total Skipped: 0

✓ Phase 1 Task 1.3: PASSED - Detection & Tracking Stable
```

**Step 1.3.2: Manual Testing (if automated tests fail)**

```python
# Test 1: Detection
from src.detection.vehicle_detector import VehicleDetector
import numpy as np

detector = VehicleDetector(model_name="yolov8n.pt")
dummy_frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
results = detector.detect(dummy_frame)
print(f"✓ Detected {len(results)} objects")

# Test 2: Tracking
from src.tracking.deepsort_tracker import DeepSORT

tracker = DeepSORT()
tracked = tracker.update(results)
print(f"✓ Tracked {len(tracked)} objects")
```

**Step 1.3.3: Load Real Model (Optional)**

If you have a sample video:
```python
from src.vision.video_processor import VideoProcessor

processor = VideoProcessor("sample_video.mp4")
results = processor.process()
print(f"Processed {results['frame_count']} frames")
print(f"Average FPS: {results['avg_fps']}")
```

✅ **Task 1.3 Complete** when:
- All tests pass
- Detection accuracy >85%
- Tracking maintains object IDs
- Processing speed >20 FPS

---

## ✅ TASK 1.4: Integration Testing & Validation

### Goal
Ensure all Phase 1 components work together

### ✅ Validation Checklist

**Dashboard Validation:**
- [ ] Dashboard loads on `http://localhost:8501`
- [ ] All tabs render without errors
- [ ] Metrics update correctly
- [ ] Real-time data displays
- [ ] No console errors

**Backend Validation:**
- [ ] API responds on `http://localhost:8000`
- [ ] Health endpoint returns healthy status
- [ ] Database queries work
- [ ] All endpoints return valid responses
- [ ] CORS enabled for dashboard

**Detection & Tracking Validation:**
- [ ] Vehicle detector initializes
- [ ] DeepSORT tracker initializes  
- [ ] End-to-end pipeline works
- [ ] Models load without errors
- [ ] Processing speed acceptable

**System Validation:**
- [ ] Services survive 5+ minute runtime
- [ ] No memory leaks observed
- [ ] Error logs are clean
- [ ] Database integrity maintained

### Run Full Validation

```bash
# 1. Ensure all services are running (3 terminals)
# Terminal 1: FastAPI
python -m uvicorn src.api.main_api:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Streamlit
python -m streamlit run src/dashboard/app.py

# Terminal 3: Run tests
python phase1_test_detection_tracking.py
```

### Expected Results

All 5 tests pass:
```
✓ DETECTION       : PASSED
✓ TRACKING        : PASSED
✓ PIPELINE        : PASSED
✓ DATABASE        : PASSED
✓ API             : PASSED
```

✅ **Phase 1 Complete** when all tests pass

---

## 🎯 Phase 1 Success Criteria

### Checklist
- [ ] Dashboard loads without "Network issue" error
- [ ] Backend API running and responding
- [ ] Detection model working (>85% accuracy)
- [ ] Tracking maintaining object IDs properly
- [ ] Database connected and operational
- [ ] All services survive 5+ minute runtime
- [ ] Test suite reports all PASSED

### Performance Targets
- Dashboard load time: <2 seconds
- Detection accuracy: >85%
- Tracking consistency: >90%
- API response time: <100ms
- System uptime: >99%

---

## 🐛 Troubleshooting

### Problem: "Address already in use" for port 8000

```bash
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID)
taskkill /PID <PID> /F

# Or change port in startup
python -m uvicorn src.api.main_api:app --reload --port 8001
```

### Problem: "No module named 'src'"

```bash
# Make sure you're in project root
cd f:\traffic_project

# Add project to Python path
set PYTHONPATH=%cd%
python phase1_test_detection_tracking.py
```

### Problem: YOLO model download stuck

```bash
# Manually download model
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# Or use smaller model
python -c "from ultralytics import YOLO; YOLO('yolov8s.pt')"
```

### Problem: Dashboard shows "No live counts found"

- Ensure data CSV files exist in `./data/` directory
- Run `main_pipeline.py` first to generate data
- Check file permissions

---

## 📞 Quick Reference Commands

```bash
# Start FastAPI
python -m uvicorn src.api.main_api:app --reload --host 0.0.0.0 --port 8000

# Start Streamlit
python -m streamlit run src/dashboard/app.py

# Run Phase 1 tests
python phase1_test_detection_tracking.py

# Test API
curl http://localhost:8000/health

# Check running services
netstat -ano | findstr :8000
netstat -ano | findstr :8501

# Kill service (Windows)
taskkill /PID <PID> /F
```

---

## 📊 Timeline

- **Day 1-2:** Complete Tasks 1.1 & 1.2
- **Day 3-4:** Complete Task 1.3
- **Day 5:** Task 1.4 validation & testing
- **Day 6-7:** Bug fixes & optimization

---

## ✨ Next Steps After Phase 1

Once Phase 1 is complete:
1. ✅ Proceed to Phase 2: Core Violation Detection
2. ✅ Implement red-light detection
3. ✅ Implement speed detection
4. ✅ Implement ANPR integration

---

**Last Updated:** May 3, 2026  
**Created by:** Development Team  
**Status:** 🟢 READY TO START
