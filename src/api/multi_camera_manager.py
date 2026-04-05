"""
Feature 10: Multi-Camera Parallel Processing
---------------------------------------------
Uses Python asyncio to manage multiple RTSP camera streams concurrently.
Each camera runs its own processing task on the event loop.
CPU-managed orchestration — GPU is shared via ModelManager singleton.
VRAM stays bounded since all cameras share ONE YOLO model.
"""

import asyncio
import cv2
import logging
import yaml
from pathlib import Path
from typing import Dict, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

class CameraStream:
    """Manages a single RTSP/video stream with non-blocking frame reading."""

    def __init__(self, camera_id: str, source: str, name: str = ""):
        self.camera_id = camera_id
        self.source = source
        self.name = name or camera_id
        self.cap = None
        self.is_active = False
        self.frame_count = 0
        self.last_frame_time = None

    def open(self) -> bool:
        self.cap = cv2.VideoCapture(self.source)
        self.is_active = self.cap.isOpened()
        if self.is_active:
            logger.info(f"Camera {self.camera_id} ({self.name}) opened: {self.source}")
        else:
            logger.error(f"Camera {self.camera_id} FAILED to open: {self.source}")
        return self.is_active

    def read_frame(self):
        if not self.is_active or self.cap is None:
            return None
        ret, frame = self.cap.read()
        if ret:
            self.frame_count += 1
            self.last_frame_time = datetime.now()
            return frame
        return None

    def release(self):
        if self.cap:
            self.cap.release()
        self.is_active = False
        logger.info(f"Camera {self.camera_id} released.")


class MultiCameraManager:
    """
    Coordinates multiple camera streams using asyncio.
    Each camera gets its own async task — they run concurrently on the event loop.
    All GPU inference happens via the shared ModelManager (stays within 4GB VRAM).
    """

    def __init__(self, cameras_config_path: str = 'config/cameras.yaml'):
        self.streams: Dict[str, CameraStream] = {}
        self.config_path = cameras_config_path
        self._load_cameras()

    def _load_cameras(self):
        """Load camera definitions from cameras.yaml."""
        if not Path(self.config_path).exists():
            logger.warning(f"cameras.yaml not found at {self.config_path}. No cameras loaded.")
            return

        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)

        for cam_key, cam_info in config.get('cameras', {}).items():
            cam_id = cam_info.get('id', cam_key)
            source = cam_info.get('rtsp_url', '')
            name = cam_info.get('name', cam_key)

            stream = CameraStream(
                camera_id=cam_id,
                source=source,
                name=name
            )
            self.streams[cam_id] = stream
            logger.info(f"Registered camera: {cam_id} ({name})")

    def add_stream(self, camera_id: str, source: str, name: str = ""):
        """Manually add a camera stream."""
        self.streams[camera_id] = CameraStream(camera_id, source, name)

    async def _process_camera(
        self,
        stream: CameraStream,
        frame_processor: Callable,
        frame_skip: int = 2
    ):
        """
        Async task for a single camera stream.
        
        Args:
            stream:          CameraStream instance
            frame_processor: Callable(frame, camera_id) → processed_frame
            frame_skip:      Process every Nth frame (reduces GPU load)
        """
        if not stream.open():
            return

        logger.info(f"Processing started for Camera {stream.camera_id}")
        loop = asyncio.get_event_loop()

        try:
            while stream.is_active:
                # Read frame in thread pool to avoid blocking event loop
                frame = await loop.run_in_executor(None, stream.read_frame)

                if frame is None:
                    logger.warning(f"Camera {stream.camera_id}: stream ended or dropped frame.")
                    await asyncio.sleep(0.5)
                    continue

                # Skip intermediate frames to reduce GPU load on RTX 2050
                if stream.frame_count % frame_skip == 0:
                    # Run inference in executor (keeps event loop responsive)
                    processed = await loop.run_in_executor(
                        None, frame_processor, frame, stream.camera_id
                    )

                    # Display (non-blocking)
                    if processed is not None:
                        cv2.imshow(f"TIS — {stream.name} ({stream.camera_id})", processed)

                # Allow other tasks to run
                await asyncio.sleep(0.001)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        except Exception as e:
            logger.error(f"Camera {stream.camera_id} processing error: {e}")
        finally:
            stream.release()

    async def run_all(self, frame_processor: Callable, frame_skip: int = 2):
        """
        Run all registered cameras concurrently.
        
        Args:
            frame_processor: Function (frame, camera_id) → annotated_frame
            frame_skip:      Process every Nth frame (default 2 for RTX 2050)
        """
        if not self.streams:
            logger.error("No camera streams registered.")
            return

        logger.info(f"Starting {len(self.streams)} camera streams concurrently...")
        tasks = [
            self._process_camera(stream, frame_processor, frame_skip)
            for stream in self.streams.values()
        ]
        await asyncio.gather(*tasks)
        cv2.destroyAllWindows()

    def get_status(self) -> Dict:
        """Return health status of all registered cameras."""
        return {
            cam_id: {
                "name": stream.name,
                "is_active": stream.is_active,
                "frames_processed": stream.frame_count,
                "last_frame_time": stream.last_frame_time.isoformat() if stream.last_frame_time else None
            }
            for cam_id, stream in self.streams.items()
        }
