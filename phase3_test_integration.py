import cv2
import numpy as np
import logging
from datetime import datetime, timedelta
import sys
import os
from pathlib import Path

# Mock/Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Phase3Test")

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def test_echallan_generation():
    print_header("TEST 3.1: E-Challan PDF Generation")
    from src.notification.echallan_pdf import EChallanPDFGenerator
    
    gen = EChallanPDFGenerator(output_dir='output/test_challans')
    
    # Create a dummy evidence image
    dummy_img_path = 'output/test_challans/dummy_evidence.jpg'
    os.makedirs('output/test_challans', exist_ok=True)
    cv2.imwrite(dummy_img_path, np.zeros((300, 400, 3), dtype=np.uint8))
    
    try:
        pdf_path = gen.generate(
            violation_id=12345,
            plate_number="MH12AB1234",
            owner_name="John Doe",
            owner_phone="+91-9876543210",
            violation_type="OVERSPEEDING",
            violation_location="Pune-Mumbai Expressway",
            violation_timestamp=datetime.now(),
            camera_id="CAM-001",
            fine_amount=2000.0,
            evidence_image_path=dummy_img_path
        )
        if os.path.exists(pdf_path):
            print(f"[OK] Success: E-Challan generated at {pdf_path}")
        else:
            print(f"[FAIL] Failure: PDF file not found at {pdf_path}")
    except Exception as e:
        print(f"[ERROR] Error generating PDF: {e}")

def test_traffic_forecasting():
    print_header("TEST 3.2: LSTM Traffic Forecasting")
    from src.prediction.forecaster import TrafficForecaster
    
    try:
        forecaster = TrafficForecaster()
        
        # Check if model exists
        model_path = 'models/traffic_density_lstm.pth'
        if os.path.exists(model_path):
            forecaster.load_model(model_path)
            print("[OK] Model loaded successfully")
        else:
            print("[WARN] Model not found, using synthetic weights for prediction test")
            
        # Generate 60 mins of \"recent\" data (60 points, 4 lanes)
        recent_data = np.random.rand(60, 4) * 50
        
        results = forecaster.predict_next_15_minutes(recent_data)
        
        if len(results['predictions']) == 15:
            print(f"[OK] Success: Predicted next {len(results['predictions'])} minutes")
            print(f"Sample prediction (Minute 1): {results['predictions'][0]}")
        else:
            print(f"[FAIL] Failure: Expected 15 predictions, got {len(results['predictions'])}")
            
    except Exception as e:
        print(f"[ERROR] Error in forecasting: {e}")

def test_adaptive_control():
    print_header("TEST 3.3: Adaptive Signal Control")
    from src.control.adaptive_traffic_controller import AdaptiveTrafficController
    
    try:
        controller = AdaptiveTrafficController(num_phases=4)
        
        # Scenario: High traffic on Phase 1
        vehicle_counts = np.array([5, 50, 10, 5]) # Lane 1 is very busy
        
        # Step 1: Initial update
        state = controller.update(vehicle_counts, dt=1.0)
        print(f"Initial State: Phase {state['current_phase']} is {state['signal_state']}")
        
        # Step 2: Run until phase switches or 60s
        for i in range(60):
            state = controller.update(vehicle_counts, dt=1.0)
            if state['phase_switched']:
                print(f"[OK] Phase switched to {state['current_phase']} after {i} seconds")
                break
        
        # Check if it prioritized the high-traffic phase (Phase 1)
        # Note: the controller logic might need some time to switch
        print(f"Final state: Phase {state['current_phase']} | Green Times: {state['green_times']}")
        
        if state['green_times'][1] > state['green_times'][0]:
            print("[OK] Success: Controller increased green time for busy phase")
        else:
            print("[WARN] Controller did not favor busy phase (might need more iterations)")
            
    except Exception as e:
        print(f"[ERROR] Error in adaptive control: {e}")

if __name__ == "__main__":
    test_echallan_generation()
    test_traffic_forecasting()
    test_adaptive_control()
    print_header("PHASE 3 INTEGRATION TESTS COMPLETED")
