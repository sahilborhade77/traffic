"""
Multi-Camera Launcher — runs all cameras from cameras.yaml simultaneously.
Uses asyncio so all streams share the single TIS process and ModelManager.
"""
import asyncio
import sys
import os
sys.path.append(os.getcwd())

from main import TrafficEnforcementSystem
from src.api.multi_camera_manager import MultiCameraManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MultiCam")

async def main():
    tis = TrafficEnforcementSystem(config_path='config/cameras.yaml')
    cam_mgr = MultiCameraManager(cameras_config_path='config/cameras.yaml')

    logger.info(f"Launching {len(cam_mgr.streams)} camera streams...")
    await cam_mgr.run_all(
        frame_processor=tis.process_frame,
        frame_skip=2  # Process every 2nd frame — optimal for RTX 2050
    )

if __name__ == "__main__":
    asyncio.run(main())
