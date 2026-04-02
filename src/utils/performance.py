"""
Performance Optimization Module

Provides performance enhancements for critical sections:
- Numba JIT compilation for heavy numerical operations
- Batch processing for multiple frames
- Async I/O for camera reads
- Vectorized operations for lane containment tests

Usage:
    from src.utils.performance import (
        compute_distances_vectorized,
        async_frame_reader,
        batch_detect
    )

Author: Traffic Intelligence Team
Version: 1.0.0
"""

import numpy as np
import asyncio
import cv2
from typing import List, Tuple, Dict, Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import time
from functools import wraps

try:
    from numba import jit, prange
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    print("Warning: numba not available, some optimizations disabled")


@dataclass
class BatchResult:
    """Result from batch processing."""
    batch_id: int
    frame_ids: List[int]
    results: List[Any]
    duration_ms: float
    success: bool = True


# ============================================================================
# NUMBA JIT-COMPILED FUNCTIONS
# ============================================================================

if NUMBA_AVAILABLE:
    @jit(nopython=True, parallel=True, cache=True)
    def compute_distances_numba(points: np.ndarray, centroid: np.ndarray) -> np.ndarray:
        """
        Compute Euclidean distances from multiple points to centroid using Numba.
        
        Args:
            points: Array of shape (n, 2) with x, y coordinates
            centroid: Array of shape (2,) with centroid x, y
            
        Returns:
            Array of shape (n,) with distances
        """
        distances = np.zeros(len(points))
        
        for i in prange(len(points)):
            dx = points[i, 0] - centroid[0]
            dy = points[i, 1] - centroid[1]
            distances[i] = np.sqrt(dx * dx + dy * dy)
        
        return distances
    
    
    @jit(nopython=True, parallel=True, cache=True)
    def point_in_polygon_vectorized(
        points: np.ndarray,
        polygon: np.ndarray
    ) -> np.ndarray:
        """
        Ray casting algorithm for point-in-polygon test (vectorized).
        
        Args:
            points: Array of shape (n, 2) with x, y coordinates
            polygon: Array of shape (m, 2) with polygon vertices
            
        Returns:
            Array of shape (n,) with boolean values (True if inside)
        """
        inside = np.zeros(len(points), dtype=np.bool_)
        
        for i in range(len(points)):
            x, y = points[i, 0], points[i, 1]
            
            # Ray casting algorithm
            inside_count = 0
            for j in range(len(polygon)):
                x1, y1 = polygon[j, 0], polygon[j, 1]
                x2, y2 = polygon[(j + 1) % len(polygon), 0], polygon[(j + 1) % len(polygon), 1]
                
                if ((y1 <= y < y2) or (y2 <= y < y1)):
                    xinters = (y - y1) * (x2 - x1) / (y2 - y1) + x1
                    if x < xinters:
                        inside_count += 1
            
            inside[i] = inside_count % 2 == 1
        
        return inside
    
    
    @jit(nopython=True, cache=True)
    def iou_numba(box1: np.ndarray, box2: np.ndarray) -> float:
        """
        Calculate Intersection over Union (IoU) for bounding boxes using Numba.
        
        Args:
            box1: Array [x1, y1, x2, y2]
            box2: Array [x1, y1, x2, y2]
            
        Returns:
            IoU score between 0 and 1
        """
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2
        
        # Intersection
        inter_x_min = max(x1_min, x2_min)
        inter_y_min = max(y1_min, y2_min)
        inter_x_max = min(x1_max, x2_max)
        inter_y_max = min(y1_max, y2_max)
        
        inter_area = max(0.0, inter_x_max - inter_x_min) * max(0.0, inter_y_max - inter_y_min)
        
        # Union
        box1_area = (x1_max - x1_min) * (y1_max - y1_min)
        box2_area = (x2_max - x2_min) * (y2_max - y2_min)
        union_area = box1_area + box2_area - inter_area
        
        if union_area == 0:
            return 0.0
        
        return inter_area / union_area

else:
    # Fallback pure Python implementations
    
    def compute_distances_numba(points: np.ndarray, centroid: np.ndarray) -> np.ndarray:
        """Fallback: compute distances without Numba."""
        return np.linalg.norm(points - centroid, axis=1)
    
    
    def point_in_polygon_vectorized(points: np.ndarray, polygon: np.ndarray) -> np.ndarray:
        """Fallback: point-in-polygon using OpenCV."""
        inside = np.zeros(len(points), dtype=bool)
        for i, point in enumerate(points):
            result = cv2.pointPolygonTest(polygon, tuple(point), False)
            inside[i] = result >= 0
        return inside
    
    
    def iou_numba(box1: np.ndarray, box2: np.ndarray) -> float:
        """Fallback: IoU calculation."""
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2
        
        inter_area = max(0, min(x1_max, x2_max) - max(x1_min, x2_min)) * \
                     max(0, min(y1_max, y2_max) - max(y1_min, y2_min))
        
        union_area = (x1_max - x1_min) * (y1_max - y1_min) + \
                     (x2_max - x2_min) * (y2_max - y2_min) - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0


# ============================================================================
# VECTORIZED OPERATIONS
# ============================================================================

def batch_iou(boxes1: np.ndarray, boxes2: np.ndarray) -> np.ndarray:
    """
    Compute IoU between all pairs of boxes (vectorized).
    
    Args:
        boxes1: Array of shape (n, 4) with [x1, y1, x2, y2]
        boxes2: Array of shape (m, 4) with [x1, y1, x2, y2]
        
    Returns:
        Array of shape (n, m) with IoU values
    """
    n = len(boxes1)
    m = len(boxes2)
    iou_matrix = np.zeros((n, m))
    
    for i in range(n):
        for j in range(m):
            iou_matrix[i, j] = iou_numba(boxes1[i], boxes2[j])
    
    return iou_matrix


def nms_vectorized(
    boxes: np.ndarray,
    scores: np.ndarray,
    iou_threshold: float = 0.5
) -> np.ndarray:
    """
    Non-Maximum Suppression (vectorized).
    
    Args:
        boxes: Array of shape (n, 4) with [x1, y1, x2, y2]
        scores: Array of shape (n,) with confidence scores
        iou_threshold: IoU threshold for suppression
        
    Returns:
        Indices of kept boxes
    """
    if len(boxes) == 0:
        return np.array([])
    
    # Sort by score
    sorted_indices = np.argsort(-scores)
    
    keep = []
    while len(sorted_indices) > 0:
        current = sorted_indices[0]
        keep.append(current)
        
        if len(sorted_indices) == 1:
            break
        
        # Compute IoU with remaining boxes
        current_box = boxes[current:current+1]
        remaining_boxes = boxes[sorted_indices[1:]]
        
        ious = batch_iou(current_box, remaining_boxes).flatten()
        
        # Keep boxes with IoU below threshold
        keep_mask = ious <= iou_threshold
        sorted_indices = sorted_indices[1:][keep_mask]
    
    return np.array(keep)


# ============================================================================
# BATCH PROCESSING
# ============================================================================

class BatchProcessor:
    """Process multiple frames in batches for efficiency."""
    
    def __init__(
        self,
        batch_size: int = 8,
        worker_threads: int = 4,
        timeout_sec: float = 30.0
    ):
        """
        Initialize batch processor.
        
        Args:
            batch_size: Number of frames per batch
            worker_threads: Number of worker threads
            timeout_sec: Timeout for batch processing
        """
        self.batch_size = batch_size
        self.executor = ThreadPoolExecutor(max_workers=worker_threads)
        self.timeout_sec = timeout_sec
        self.batch_id = 0
    
    def process_batch(
        self,
        frames: List[np.ndarray],
        process_func: Callable,
        *args,
        **kwargs
    ) -> BatchResult:
        """
        Process batch of frames.
        
        Args:
            frames: List of frames to process
            process_func: Function to apply to each frame
            *args: Positional arguments for process_func
            **kwargs: Keyword arguments for process_func
            
        Returns:
            BatchResult with processing results
        """
        start_time = time.time()
        self.batch_id += 1
        
        try:
            # Process frames in parallel
            futures = []
            frame_ids = list(range(len(frames)))
            
            for i, frame in enumerate(frames):
                future = self.executor.submit(
                    process_func,
                    frame,
                    *args,
                    **kwargs
                )
                futures.append(future)
            
            # Collect results
            results = []
            for future in futures:
                result = future.result(timeout=self.timeout_sec)
                results.append(result)
            
            duration_ms = (time.time() - start_time) * 1000
            
            return BatchResult(
                batch_id=self.batch_id,
                frame_ids=frame_ids,
                results=results,
                duration_ms=duration_ms,
                success=True
            )
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            return BatchResult(
                batch_id=self.batch_id,
                frame_ids=list(range(len(frames))),
                results=[],
                duration_ms=duration_ms,
                success=False
            )


# ============================================================================
# ASYNC I/O
# ============================================================================

class AsyncFrameReader:
    """
    Asynchronous frame reading from camera/video with pre-buffering.
    
    Reduces latency by reading frames in parallel with processing.
    """
    
    def __init__(
        self,
        video_source: str,
        buffer_size: int = 30,
        read_timeout_sec: float = 5.0
    ):
        """
        Initialize async frame reader.
        
        Args:
            video_source: Camera ID, RTSP URL, or video file path
            buffer_size: Size of frame buffer
            read_timeout_sec: Timeout for frame reads
        """
        self.video_source = video_source
        self.buffer_size = buffer_size
        self.read_timeout_sec = read_timeout_sec
        
        self.cap = None
        self.frame_queue = asyncio.Queue(maxsize=buffer_size)
        self.reading = False
        self.frame_count = 0
    
    async def __aenter__(self):
        """Async context manager entry."""
        # Open video capture
        self.cap = cv2.VideoCapture(self.video_source)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open video source: {self.video_source}")
        
        # Start background reader
        self.reading = True
        asyncio.create_task(self._read_loop())
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.reading = False
        if self.cap:
            self.cap.release()
    
    async def _read_loop(self):
        """Background loop that reads frames into queue."""
        loop = asyncio.get_event_loop()
        
        try:
            while self.reading:
                # Read in executor to avoid blocking
                ret, frame = await loop.run_in_executor(
                    None,
                    self.cap.read
                )
                
                if not ret:
                    break
                
                self.frame_count += 1
                
                try:
                    # Add to queue with timeout
                    await asyncio.wait_for(
                        self.frame_queue.put((self.frame_count, frame)),
                        timeout=self.read_timeout_sec
                    )
                except asyncio.TimeoutError:
                    # Queue full, skip frame to maintain real-time performance
                    pass
        
        except Exception as e:
            print(f"Error in frame reader loop: {e}")
        finally:
            self.reading = False
    
    async def get_frame(self) -> Tuple[int, np.ndarray]:
        """
        Get next frame from buffer.
        
        Returns:
            Tuple of (frame_number, frame_data)
        """
        return await asyncio.wait_for(
            self.frame_queue.get(),
            timeout=self.read_timeout_sec
        )
    
    def queue_size(self) -> int:
        """Get current queue size."""
        return self.frame_queue.qsize()


# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================

def performance_timer(func: Callable) -> Callable:
    """
    Decorator to measure function execution time.
    
    Usage:
        @performance_timer
        def expensive_operation():
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration_ms = (time.time() - start) * 1000
        
        print(f"{func.__name__}: {duration_ms:.2f}ms")
        
        return result
    
    return wrapper


class TimingContext:
    """Context manager for performance timing."""
    
    def __init__(self, name: str = "operation", log_func=None):
        """
        Initialize timing context.
        
        Args:
            name: Operation name
            log_func: Logger function to use
        """
        self.name = name
        self.log_func = log_func or print
        self.start_time = None
        self.duration_ms = 0
    
    def __enter__(self):
        """Enter context."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and log duration."""
        self.duration_ms = (time.time() - self.start_time) * 1000
        self.log_func(f"{self.name}: {self.duration_ms:.2f}ms")


# ============================================================================
# MEMORY EFFICIENCY
# ============================================================================

class FrameCache:
    """
    Efficient frame caching with automatic memory management.
    """
    
    def __init__(self, max_frames: int = 100):
        """
        Initialize frame cache.
        
        Args:
            max_frames: Maximum frames to cache before LRU eviction
        """
        self.max_frames = max_frames
        self.frames = {}  # frame_id -> frame
        self.access_order = []  # LRU tracking
    
    def put(self, frame_id: int, frame: np.ndarray) -> None:
        """
        Cache a frame.
        
        Args:
            frame_id: Unique frame identifier
            frame: Frame data
        """
        if frame_id in self.frames:
            self.access_order.remove(frame_id)
        
        self.frames[frame_id] = frame
        self.access_order.append(frame_id)
        
        # Evict oldest if exceeds limit
        while len(self.frames) > self.max_frames:
            oldest_id = self.access_order.pop(0)
            del self.frames[oldest_id]
    
    def get(self, frame_id: int) -> Optional[np.ndarray]:
        """
        Retrieve cached frame.
        
        Args:
            frame_id: Frame identifier
            
        Returns:
            Frame data or None if not cached
        """
        if frame_id in self.frames:
            # Update access order
            self.access_order.remove(frame_id)
            self.access_order.append(frame_id)
            return self.frames[frame_id]
        
        return None
    
    def clear(self) -> None:
        """Clear cache."""
        self.frames.clear()
        self.access_order.clear()


# ============================================================================
# OPTIMIZATION UTILITIES
# ============================================================================

def optimize_frame_resolution(
    frame: np.ndarray,
    target_height: int = 480
) -> np.ndarray:
    """
    Optimize frame resolution for processing.
    
    Args:
        frame: Input frame
        target_height: Target height in pixels
        
    Returns:
        Resized frame maintaining aspect ratio
    """
    height = frame.shape[0]
    width = frame.shape[1]
    
    if height == target_height:
        return frame
    
    scale = target_height / height
    new_width = int(width * scale)
    
    return cv2.resize(frame, (new_width, target_height), interpolation=cv2.INTER_LINEAR)


def profile_function(func: Callable, *args, iterations: int = 100, **kwargs) -> Dict:
    """
    Profile function performance.
    
    Args:
        func: Function to profile
        iterations: Number of iterations
        *args, **kwargs: Arguments to function
        
    Returns:
        Dictionary with timing statistics
    """
    times = []
    
    for _ in range(iterations):
        start = time.time()
        func(*args, **kwargs)
        times.append((time.time() - start) * 1000)
    
    times = np.array(times)
    
    return {
        'iterations': iterations,
        'mean_ms': np.mean(times),
        'median_ms': np.median(times),
        'min_ms': np.min(times),
        'max_ms': np.max(times),
        'std_ms': np.std(times),
    }
