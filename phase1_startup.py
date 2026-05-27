#!/usr/bin/env python3
"""
Phase 1: Service Startup Script
Starts all required services for the Traffic Intelligence System
"""

import subprocess
import time
import sys
import os
import requests
from pathlib import Path

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}✗ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠ {text}{RESET}")

def check_environment():
    """Verify .env file and required directories exist"""
    print_header("Phase 1: Environment Check")
    
    # Check .env
    if not Path('.env').exists():
        print_error(".env file not found")
        return False
    print_success(".env file found")
    
    # Check required directories
    required_dirs = ['data', 'models', 'logs', 'cache', 'src']
    for dir_name in required_dirs:
        if not Path(dir_name).exists():
            print_warning(f"Creating {dir_name} directory...")
            Path(dir_name).mkdir(exist_ok=True)
        print_success(f"{dir_name} directory ready")
    
    return True

def check_python_packages():
    """Verify required packages are installed"""
    print_header("Phase 1: Package Verification")
    
    required_packages = [
        'streamlit',
        'fastapi',
        'uvicorn',
        'torch',
        'torchvision',
        'ultralytics',
        'opencv-python',
        'pandas',
        'numpy',
        'sqlalchemy',
        'plotly'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print_success(f"{package} installed")
        except ImportError:
            print_error(f"{package} NOT installed")
            missing_packages.append(package)
    
    if missing_packages:
        print_error(f"Missing packages: {', '.join(missing_packages)}")
        print_warning("Run: pip install -r requirements.txt")
        return False
    
    return True

def check_api_health(host='localhost', port=8000, max_retries=5):
    """Check if API is healthy"""
    print_header("Phase 1: API Health Check")
    
    url = f"http://{host}:{port}/health"
    retries = 0
    
    while retries < max_retries:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print_success(f"API is healthy at {url}")
                return True
        except requests.exceptions.RequestException:
            retries += 1
            print_warning(f"API not ready, retrying... ({retries}/{max_retries})")
            time.sleep(2)
    
    print_error("API health check failed - API not responding")
    return False

def start_backend():
    """Start FastAPI backend"""
    print_header("Phase 1: Starting Backend (FastAPI)")
    
    print("Starting FastAPI server on http://0.0.0.0:8000")
    print_warning("Keep this terminal open or run in a new terminal tab")
    print_warning("Press Ctrl+C to stop\n")
    
    cmd = [
        sys.executable, 
        '-m', 
        'uvicorn', 
        'src.api.main_api:app',
        '--reload',
        '--host', '0.0.0.0',
        '--port', '8000'
    ]
    
    try:
        subprocess.Popen(cmd)
        print_success("FastAPI server started")
        return True
    except Exception as e:
        print_error(f"Failed to start FastAPI: {e}")
        return False

def start_streamlit():
    """Start Streamlit dashboard"""
    print_header("Phase 1: Starting Dashboard (Streamlit)")
    
    print("Starting Streamlit app on http://localhost:8501")
    print_warning("Keep this terminal open or run in a new terminal tab")
    print_warning("Press Ctrl+C to stop\n")
    
    cmd = [
        sys.executable,
        '-m',
        'streamlit',
        'run',
        'src/dashboard/app.py'
    ]
    
    try:
        subprocess.Popen(cmd)
        print_success("Streamlit app started")
        return True
    except Exception as e:
        print_error(f"Failed to start Streamlit: {e}")
        return False

def start_detection_service():
    """Test detection service"""
    print_header("Phase 1: Testing Detection Service")
    
    try:
        from src.detection.vehicle_detector import VehicleDetector
        print("Loading YOLOv8 model...")
        detector = VehicleDetector(model_name="yolov8n.pt")
        print_success("VehicleDetector loaded successfully")
        return True
    except Exception as e:
        print_error(f"Failed to load detection model: {e}")
        return False

def start_tracking_service():
    """Test tracking service"""
    print_header("Phase 1: Testing Tracking Service")
    
    try:
        from src.tracking.deepsort_tracker import DeepSORT
        print("Initializing DeepSORT tracker...")
        tracker = DeepSORT()
        print_success("DeepSORT tracker initialized successfully")
        return True
    except Exception as e:
        print_error(f"Failed to initialize tracker: {e}")
        return False

def main():
    """Main startup sequence"""
    print_header("PHASE 1: Smart AI Traffic Intelligence System - Startup Sequence")
    
    # Step 1: Environment check
    if not check_environment():
        print_error("Environment check failed")
        sys.exit(1)
    
    # Step 2: Package verification
    if not check_python_packages():
        print_error("Package verification failed")
        sys.exit(1)
    
    # Step 3: Test detection service
    if not start_detection_service():
        print_warning("Detection service test skipped - model may need download")
    
    # Step 4: Test tracking service
    if not start_tracking_service():
        print_warning("Tracking service test skipped")
    
    # Step 5: Start backend
    print_header("Ready to Start Services")
    print("Choose startup mode:")
    print("1. Start Backend + Dashboard (Auto)")
    print("2. Start Backend only")
    print("3. Start Dashboard only")
    print("4. Exit\n")
    
    choice = input("Enter choice (1-4): ").strip()
    
    if choice == '1':
        print_warning("\nIMPORTANT: You need 2 terminal windows or 2 terminal tabs!")
        print("This script will start both services sequentially.")
        print("To use 2 terminals, run these commands separately:\n")
        print(f"  Terminal 1: {BLUE}.venv\\Scripts\\python -m uvicorn src.api.main_api:app --reload{RESET}")
        print(f"  Terminal 2: {BLUE}.venv\\Scripts\\streamlit run src/dashboard/app.py{RESET}\n")
        
        response = input("Continue with this terminal? (y/n): ").strip().lower()
        if response == 'y':
            start_backend()
            time.sleep(3)
            check_api_health()
    elif choice == '2':
        start_backend()
    elif choice == '3':
        start_streamlit()
    else:
        print("Exiting...")
        sys.exit(0)
    
    print_header("Phase 1: Services Started Successfully")
    print(f"{GREEN}Dashboard: http://localhost:8501{RESET}")
    print(f"{GREEN}API: http://localhost:8000{RESET}")
    print(f"{GREEN}API Docs: http://localhost:8000/docs{RESET}\n")
    
    input("Press Enter to continue monitoring...")

if __name__ == '__main__':
    main()
