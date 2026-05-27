import asyncio
import cv2
import numpy as np
import logging
from datetime import datetime, timedelta
import random
from src.api.multi_camera_manager import MultiCameraManager
from src.violations.average_speed_enforcer import AverageSpeedEnforcer

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MultiCamDemo")

class MultiCamSystem:
    def __init__(self):
        # 1. Initialize Multi-Camera Manager
        self.manager = MultiCameraManager(cameras_config_path='config/cameras.yaml')
        
        # 2. Initialize Average Speed Enforcer for Zone North (CAM_001 -> CAM_002)
        self.speed_enforcer = AverageSpeedEnforcer({
            'entry_camera': 'CAM_001',
            'exit_camera': 'CAM_002',
            'distance_km': 2.5,
            'speed_limit_kmh': 60
        })
        
        # Mock detection history to simulate cross-camera tracking
        self.detected_plates = ["MH12-DE-4567", "MH14-AZ-8899", "MH01-BB-0001", "KA03-MG-1234"]

    def process_frame_logic(self, frame, camera_id):
        """
        Simulated frame processing logic.
        In real production, this would call YOLO and OCR.
        """
        # Simulate some processing time
        # cv2.putText(frame, f"CAM: {camera_id}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Randomly simulate a vehicle detection
        if random.random() < 0.05:
            plate = random.choice(self.detected_plates)
            timestamp = datetime.now()
            
            # --- Logic for Average Speed Enforcement ---
            if camera_id == "CAM_001":
                self.speed_enforcer.record_entry(plate, camera_id, timestamp)
            elif camera_id == "CAM_002":
                # Simulate entry 2 minutes ago for demo
                mock_entry_time = timestamp - timedelta(minutes=random.uniform(1.5, 5.0))
                self.speed_enforcer.entry_records[plate] = mock_entry_time 
                
                violation = self.speed_enforcer.check_exit(plate, camera_id, timestamp)
                if violation:
                    logger.warning(f"🚨 ALERT: Average Speed Violation Caught! {plate} @ {violation['avg_speed']:.1f} km/h")
                    cv2.putText(frame, "VIOLATION: SPEED", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        return frame

    async def run(self):
        # In this demo, we use simulated streams (blank frames) 
        # since we don't have real RTSP cameras connected.
        # But the logic remains identical.
        
        logger.info("Starting Multi-Camera Intelligence Pipeline...")
        
        # Start the parallel processing loop
        # We pass self.process_frame_logic as the frame_processor
        await self.manager.run_all(frame_processor=self.process_frame_logic, frame_skip=1)

if __name__ == "__main__":
    # Note: This demo requires the 'rtsp_url' in config/cameras.yaml to be valid 
    # or replaced with a local video file path for testing.
    # For this task, we will mock the CameraStream to use a blank generator.
    
    import src.api.multi_camera_manager as mcm
    
    # Mocking CameraStream to avoid real RTSP errors during automated test
    class MockStream(mcm.CameraStream):
        def open(self):
            self.is_active = True
            return True
        def read_frame(self):
            if self.frame_count > 100: # End after 100 frames for demo
                self.is_active = False
                return None
            return np.zeros((480, 640, 3), dtype=np.uint8)

    mcm.CameraStream = MockStream # Monkey patch for demo
    
    system = MultiCamSystem()
    asyncio.run(system.run())
