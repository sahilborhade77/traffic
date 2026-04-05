#!/usr/bin/env python3
"""
Multi-Camera Processing Class

This class handles simultaneous processing of multiple video streams with
thread pooling and frame synchronization for real-time multi-camera applications.
"""

import cv2
import time
import logging
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
from typing import List, Dict, Optional, Tuple, Callable
import threading

logger = logging.getLogger(__name__)

class MultiCameraProcessor:
    """
    Handles simultaneous processing of multiple camera streams with synchronization.

    Features:
    - Thread-pooled camera capture
    - Frame synchronization across cameras
    - Configurable synchronization window
    - Graceful error handling and recovery
    """

    def __init__(self,
                 camera_sources: List[str],
                 max_workers: int = 4,
                 sync_window_ms: float = 100.0,
                 queue_size: int = 10):
        """
        Initialize the multi-camera processor.

        Args:
            camera_sources: List of camera source URLs/paths
            max_workers: Maximum number of worker threads
            sync_window_ms: Synchronization window in milliseconds
            queue_size: Maximum queue size per camera
        """
        self.camera_sources = camera_sources
        self.num_cameras = len(camera_sources)
        self.max_workers = min(max_workers, self.num_cameras)
        self.sync_window_ms = sync_window_ms / 1000.0  # Convert to seconds
        self.queue_size = queue_size

        # Threading components
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="CameraWorker")
        self.frame_queues: List[Queue] = [Queue(maxsize=queue_size) for _ in camera_sources]
        self.camera_threads: List[threading.Thread] = []
        self.processing_lock = threading.Lock()
        self.processing = False

        # Statistics
        self.stats = {
            'frames_processed': [0] * self.num_cameras,
            'frames_dropped': [0] * self.num_cameras,
            'sync_attempts': 0,
            'sync_successes': 0
        }

        logger.info(f"Initialized MultiCameraProcessor with {self.num_cameras} cameras")

    def start_processing(self) -> None:
        """
        Start processing all camera streams.
        """
        with self.processing_lock:
            if self.processing:
                logger.warning("Processing already started")
                return

            self.processing = True
            logger.info("Starting multi-camera processing...")

            # Start camera worker threads
            for i, source in enumerate(self.camera_sources):
                thread = threading.Thread(
                    target=self._camera_worker,
                    args=(i, source),
                    name=f"Camera-{i}"
                )
                thread.daemon = True
                thread.start()
                self.camera_threads.append(thread)

    def stop_processing(self) -> None:
        """
        Stop processing all camera streams.
        """
        with self.processing_lock:
            if not self.processing:
                return

            logger.info("Stopping multi-camera processing...")
            self.processing = False

            # Wait for threads to finish
            for thread in self.camera_threads:
                thread.join(timeout=2.0)

            self.executor.shutdown(wait=True)
            logger.info("Multi-camera processing stopped")

    def get_synchronized_frames(self, timeout: float = 1.0) -> Optional[Dict[int, Tuple[np.ndarray, float]]]:
        """
        Get synchronized frames from all cameras.

        Args:
            timeout: Maximum time to wait for frames

        Returns:
            Dictionary of {camera_id: (frame, timestamp)} or None if sync failed
        """
        if not self.processing:
            return None

        self.stats['sync_attempts'] += 1
        frames = {}
        start_time = time.time()

        # Collect frames from all cameras
        for camera_id in range(self.num_cameras):
            try:
                frame, timestamp = self.frame_queues[camera_id].get(timeout=timeout)
                frames[camera_id] = (frame, timestamp)
            except Empty:
                # Timeout waiting for this camera
                continue

        # Check synchronization
        if len(frames) == self.num_cameras:
            timestamps = [ts for _, ts in frames.values()]
            time_span = max(timestamps) - min(timestamps)

            if time_span <= self.sync_window_ms:
                self.stats['sync_successes'] += 1
                return frames
            else:
                # Frames not synchronized, put them back
                for camera_id, (frame, timestamp) in frames.items():
                    try:
                        self.frame_queues[camera_id].put((frame, timestamp), timeout=0.1)
                    except:
                        self.stats['frames_dropped'][camera_id] += 1

        return None

    def process_synchronized_frames(self,
                                   frame_processor: Callable[[Dict[int, Tuple[np.ndarray, float]]], None],
                                   timeout: float = 1.0) -> None:
        """
        Continuously process synchronized frames using a callback function.

        Args:
            frame_processor: Function to process synchronized frames
            timeout: Timeout for frame synchronization
        """
        logger.info("Starting synchronized frame processing...")

        try:
            while self.processing:
                synced_frames = self.get_synchronized_frames(timeout)

                if synced_frames:
                    try:
                        frame_processor(synced_frames)
                    except Exception as e:
                        logger.error(f"Error in frame processor: {e}")
                else:
                    # Small delay to prevent busy waiting
                    time.sleep(0.01)

        except KeyboardInterrupt:
            logger.info("Frame processing interrupted")
        finally:
            self.stop_processing()

    def _camera_worker(self, camera_id: int, source: str) -> None:
        """
        Worker thread for processing a single camera stream.

        Args:
            camera_id: ID of the camera
            source: Camera source URL/path
        """
        logger.info(f"Starting camera worker {camera_id} for source: {source}")

        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            logger.error(f"Failed to open camera {camera_id}: {source}")
            return

        try:
            while self.processing:
                ret, frame = cap.read()
                if not ret:
                    logger.warning(f"Failed to read frame from camera {camera_id}")
                    time.sleep(0.1)  # Brief pause before retry
                    continue

                timestamp = time.time()

                # Try to put frame in queue
                try:
                    self.frame_queues[camera_id].put((frame, timestamp), timeout=0.1)
                    self.stats['frames_processed'][camera_id] += 1
                except:
                    # Queue full, drop frame
                    self.stats['frames_dropped'][camera_id] += 1

        except Exception as e:
            logger.error(f"Error in camera worker {camera_id}: {e}")
        finally:
            cap.release()
            logger.info(f"Camera worker {camera_id} stopped")

    def get_stats(self) -> Dict:
        """
        Get processing statistics.

        Returns:
            Dictionary with processing statistics
        """
        with self.processing_lock:
            stats = self.stats.copy()
            if self.stats['sync_attempts'] > 0:
                stats['sync_success_rate'] = self.stats['sync_successes'] / self.stats['sync_attempts']
            else:
                stats['sync_success_rate'] = 0.0

            return stats

    def __enter__(self):
        """Context manager entry."""
        self.start_processing()
        return self

    def __exit__(self, exc_type, exc_val, exc_exc):
        """Context manager exit."""
        self.stop_processing()


# Example usage and testing functions
def example_frame_processor(synced_frames: Dict[int, Tuple[np.ndarray, float]]) -> None:
    """
    Example frame processor function.

    Args:
        synced_frames: Dictionary of synchronized frames
    """
    print(f"Processing synchronized frames from {len(synced_frames)} cameras at {time.time()}")

    # Here you would add your actual processing logic
    # For example: vehicle detection, analytics, etc.

def test_multi_camera():
    """
    Test function for the multi-camera processor.
    """
    # Example camera sources (replace with actual sources)
    camera_sources = [
        "data/traffic_sample.mp4",  # Local video file
        "data/traffic_sample.mp4",  # Same file for testing
        "data/traffic_sample.mp4",  # Same file for testing
        "data/traffic_sample.mp4"   # Same file for testing
    ]

    with MultiCameraProcessor(camera_sources) as processor:
        # Process for 10 seconds
        start_time = time.time()
        while time.time() - start_time < 10:
            synced_frames = processor.get_synchronized_frames(timeout=0.5)
            if synced_frames:
                example_frame_processor(synced_frames)

        # Print statistics
        stats = processor.get_stats()
        print("Processing Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

if __name__ == "__main__":
    # Run test if executed directly
    test_multi_camera()