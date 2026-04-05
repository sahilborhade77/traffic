#!/usr/bin/env python3
"""
DeepSORT-Based Vehicle Tracking

Advanced multi-object tracking for traffic analysis with:
- Individual vehicle tracking across frames
- Speed and direction calculation
- Dwell time monitoring
- Trajectory analysis
"""

import numpy as np
import cv2
import torch
import logging
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict, deque
from datetime import datetime
import time

from deep_sort_realtime.deepsort_tracker import DeepSort

logger = logging.getLogger(__name__)

class VehicleTrack:
    """
    Represents a tracked vehicle with motion and behavioral metrics.
    """

    def __init__(self,
                 track_id: int,
                 bbox: np.ndarray,
                 confidence: float,
                 class_id: int,
                 frame_id: int,
                 timestamp: float,
                 max_history: int = 30):
        """Initialize vehicle track."""
        self.track_id = track_id
        self.bbox = bbox
        self.confidence = confidence
        self.class_id = class_id
        self.frame_id = frame_id
        self.timestamp = timestamp
        self.max_history = max_history

        # Motion tracking
        self.position_history: deque = deque(maxlen=max_history)

        # Metrics
        self.speed_history: deque = deque(maxlen=max_history)
        self.direction_angles: deque = deque(maxlen=max_history)

        # Dwell time tracking
        self.dwell_zones: Dict[str, float] = defaultdict(float)
        self.centroid_position: Optional[Tuple[float, float]] = None

    def update(self, bbox: np.ndarray, confidence: float, frame_id: int, timestamp: float):
        """Update track with new detection."""
        self.bbox = bbox
        self.confidence = confidence
        self.frame_id = frame_id
        self.timestamp = timestamp
        self.centroid_position = self.get_centroid()

    def get_centroid(self) -> Tuple[float, float]:
        """Calculate centroid of bounding box."""
        x1, y1, x2, y2 = self.bbox
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        return (cx, cy)

    def add_position(self, x: float, y: float, timestamp: float):
        """Add position to history."""
        self.position_history.append((x, y, timestamp))

    def calculate_speed(self, fps: float = 30.0, pixels_per_meter: float = 10.0) -> Optional[float]:
        """
        Calculate current speed in m/s.

        Args:
            fps: Frames per second for timing
            pixels_per_meter: Conversion factor from pixels to meters

        Returns:
            Speed in m/s or None if insufficient history
        """
        if len(self.position_history) < 2:
            return None

        x1, y1, t1 = self.position_history[0]
        x2, y2, t2 = self.position_history[-1]

        if t2 == t1:
            return None

        # Euclidean distance in pixels
        distance_pixels = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        # Convert to meters
        distance_meters = distance_pixels / pixels_per_meter

        # Time in seconds
        time_seconds = t2 - t1

        # Speed in m/s
        speed = distance_meters / time_seconds

        self.speed_history.append(speed)

        return speed

    def calculate_direction(self) -> Optional[float]:
        """
        Calculate current direction as angle in degrees [0, 360).

        Returns:
            Angle in degrees or None if insufficient history
        """
        if len(self.position_history) < 2:
            return None

        x1, y1, _ = self.position_history[0]
        x2, y2, _ = self.position_history[-1]

        # Calculate angle
        dx = x2 - x1
        dy = y2 - y1

        angle = np.arctan2(dy, dx) * 180 / np.pi

        # Normalize to [0, 360)
        angle = (angle + 360) % 360

        self.direction_angles.append(angle)

        return angle

    def get_average_speed(self) -> Optional[float]:
        """Get average speed over history."""
        if not self.speed_history:
            return None
        return np.mean(list(self.speed_history))

    def get_average_direction(self) -> Optional[float]:
        """Get average direction as mean of angles."""
        if not self.direction_angles:
            return None

        # Convert angles to unit vectors, average, then back to angle
        angles = np.array(list(self.direction_angles)) * np.pi / 180
        sin_sum = np.sum(np.sin(angles))
        cos_sum = np.sum(np.cos(angles))

        avg_angle = np.arctan2(sin_sum, cos_sum) * 180 / np.pi
        return (avg_angle + 360) % 360

    def update_dwell_time(self, zone_name: str, time_delta: float):
        """Add time spent in a zone."""
        self.dwell_zones[zone_name] += time_delta


class DeepSORTTracker:
    """
    Advanced multi-object tracking using DeepSORT algorithm.
    Tracks vehicles and calculates motion-based metrics.
    """

    def __init__(self,
                 max_age: int = 30,
                 n_init: int = 3,
                 max_iou_distance: float = 0.7,
                 max_cosine_distance: float = 0.2,
                 nn_budget: int = 100,
                 fps: float = 30.0,
                 pixels_per_meter: float = 10.0):
        """
        Initialize DeepSORT tracker.

        Args:
            max_age: Maximum frames to keep track without detection
            n_init: Frames required to confirm a new track
            max_iou_distance: Maximum IOU distance for association
            max_cosine_distance: Maximum cosine distance for appearance matching
            nn_budget: Budget for appearance features
            fps: Video frames per second
            pixels_per_meter: Calibration for real-world distance
        """
        self.deepsort = DeepSort(
            max_age=max_age,
            n_init=n_init,
            max_iou_distance=max_iou_distance,
            max_cosine_distance=max_cosine_distance,
            nn_budget=nn_budget
        )

        self.fps = fps
        self.pixels_per_meter = pixels_per_meter
        self.time_per_frame = 1.0 / fps

        # Track management
        self.active_tracks: Dict[int, VehicleTrack] = {}
        self.completed_tracks: Dict[int, VehicleTrack] = {}
        self.frame_id = 0

        # Statistics
        self.total_vehicles_seen = 0
        self.vehicle_class_map = {
            2: "car",
            3: "motorcycle",
            5: "bus",
            7: "truck",
            0: "person",
            1: "bicycle"
        }

        logger.info(f"Initialized DeepSORTTracker with max_age={max_age}, n_init={n_init}")
        logger.info(f"Videos calibrated to {pixels_per_meter} pixels/meter, {fps} FPS")

    def update(self, detections: List[Tuple[List[float], float, int]], frame: np.ndarray) -> Dict[int, VehicleTrack]:
        """
        Update tracker with new detections.

        Args:
            detections: List of ([x1, y1, w, h], confidence, class_id) tuples
            frame: Current frame for appearance feature extraction

        Returns:
            Dictionary of active tracks {track_id: VehicleTrack}
        """
        self.frame_id += 1
        current_time = time.time()

        # Update DeepSORT
        tracks = self.deepsort.update_tracks(detections, frame=frame)

        # Update active tracks
        seen_track_ids = set()

        for track in tracks:
            track_id = track.track_id
            seen_track_ids.add(track_id)

            if track.is_confirmed():
                # Extract detection info - DeepSORT gives ltrb format (left, top, right, bottom)
                ltrb = track.ltrb
                bbox = np.array([ltrb[0], ltrb[1], ltrb[2], ltrb[3]])

                # Get confidence from original detections
                confidence = 0.9  # Default

                # Get class from detections
                class_id = 0

                if track_id in self.active_tracks:
                    # Update existing track
                    vehicle_track = self.active_tracks[track_id]
                    vehicle_track.update(bbox, confidence, self.frame_id, current_time)
                else:
                    # New confirmed track
                    vehicle_track = VehicleTrack(
                        track_id=track_id,
                        bbox=bbox,
                        confidence=confidence,
                        class_id=class_id,
                        frame_id=self.frame_id,
                        timestamp=current_time
                    )
                    self.active_tracks[track_id] = vehicle_track
                    self.total_vehicles_seen += 1
                    logger.debug(f"New track confirmed: ID={track_id}")

                # Add position to history
                cx, cy = vehicle_track.get_centroid()
                vehicle_track.add_position(cx, cy, current_time)

                # Calculate metrics
                vehicle_track.calculate_speed(fps=self.fps, pixels_per_meter=self.pixels_per_meter)
                vehicle_track.calculate_direction()

        # Move lost tracks to completed
        lost_track_ids = set(self.active_tracks.keys()) - seen_track_ids
        for track_id in lost_track_ids:
            track = self.active_tracks.pop(track_id)
            self.completed_tracks[track_id] = track
            logger.debug(f"Track completed: ID={track_id}, lifetime={track.frame_id - 1} frames")

        return self.active_tracks.copy()

    def get_track_info(self, track_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a track.

        Args:
            track_id: ID of the track

        Returns:
            Dictionary with track information or None
        """
        track = self.active_tracks.get(track_id) or self.completed_tracks.get(track_id)

        if track is None:
            return None

        return {
            'track_id': track.track_id,
            'class': self.vehicle_class_map.get(track.class_id, 'unknown'),
            'bbox': track.bbox.tolist(),
            'centroid': track.centroid_position,
            'current_speed': track.calculate_speed(fps=self.fps, pixels_per_meter=self.pixels_per_meter),
            'average_speed': track.get_average_speed(),
            'current_direction': track.calculate_direction(),
            'average_direction': track.get_average_direction(),
            'frame_count': self.frame_id - track.frame_id,
            'position_history_length': len(track.position_history),
            'dwell_times': dict(track.dwell_zones)
        }

    def get_active_tracks(self) -> List[Dict[str, Any]]:
        """Get information about all active tracks."""
        return [self.get_track_info(track_id) for track_id in self.active_tracks.keys()]

    def get_speed_statistics(self) -> Dict[str, float]:
        """
        Get speed statistics for all active vehicles.

        Returns:
            Dictionary with speed statistics
        """
        speeds = []

        for track in self.active_tracks.values():
            avg_speed = track.get_average_speed()
            if avg_speed is not None:
                speeds.append(avg_speed)

        if not speeds:
            return {
                'count': 0,
                'mean': 0.0,
                'std': 0.0,
                'min': 0.0,
                'max': 0.0
            }

        return {
            'count': len(speeds),
            'mean': float(np.mean(speeds)),
            'std': float(np.std(speeds)),
            'min': float(np.min(speeds)),
            'max': float(np.max(speeds))
        }

    def get_direction_statistics(self) -> Dict[str, float]:
        """
        Get direction statistics for all active vehicles.

        Returns:
            Dictionary with direction statistics
        """
        directions = []

        for track in self.active_tracks.values():
            avg_dir = track.get_average_direction()
            if avg_dir is not None:
                directions.append(avg_dir)

        if not directions:
            return {
                'count': 0,
                'dominant_direction': None
            }

        # Find dominant direction (mode)
        directions = np.array(directions)
        hist, bin_edges = np.histogram(directions, bins=8)
        dominant_idx = np.argmax(hist)
        dominant_direction = (bin_edges[dominant_idx] + bin_edges[dominant_idx + 1]) / 2

        return {
            'count': len(directions),
            'dominant_direction': float(dominant_direction),
            'directions': directions.tolist()
        }

    def draw_tracks(self,
                    frame: np.ndarray,
                    draw_trails: bool = True,
                    draw_speed: bool = True,
                    draw_direction: bool = True) -> np.ndarray:
        """
        Draw tracked vehicles and their metrics on frame.

        Args:
            frame: Input frame
            draw_trails: Whether to draw movement trails
            draw_speed: Whether to draw speed values
            draw_direction: Whether to draw direction arrows

        Returns:
            Annotated frame
        """
        annotated = frame.copy()

        for track_id, track in self.active_tracks.items():
            # Draw bounding box
            x1, y1, x2, y2 = track.bbox.astype(int)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Draw track ID
            cv2.putText(annotated, f"ID: {track_id}", (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

            # Draw speed
            if draw_speed:
                speed = track.calculate_speed(fps=self.fps, pixels_per_meter=self.pixels_per_meter)
                if speed is not None:
                    cv2.putText(annotated, f"Speed: {speed:.1f} m/s", (x1, y1 + 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

            # Draw direction
            if draw_direction:
                direction = track.calculate_direction()
                if direction is not None:
                    cx, cy = track.get_centroid()
                    cx, cy = int(cx), int(cy)

                    # Draw direction arrow
                    arrow_length = 30
                    rad = np.radians(direction)
                    end_x = int(cx + arrow_length * np.cos(rad))
                    end_y = int(cy + arrow_length * np.sin(rad))

                    cv2.arrowedLine(annotated, (cx, cy), (end_x, end_y),
                                   (255, 0, 0), 2, tipLength=0.3)

            # Draw trail
            if draw_trails and len(track.position_history) > 1:
                positions = list(track.position_history)
                for i in range(len(positions) - 1):
                    x1, y1, _ = positions[i]
                    x2, y2, _ = positions[i + 1]
                    cv2.line(annotated, (int(x1), int(y1)), (int(x2), int(y2)),
                            (200, 200, 0), 1)

        return annotated

    def reset(self):
        """Reset tracker state."""
        self.active_tracks.clear()
        self.completed_tracks.clear()
        self.frame_id = 0
        self.deepsort.__init__()  # Reinitialize DeepSORT
        logger.info("Tracker reset")

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive tracking summary."""
        return {
            'frame_id': self.frame_id,
            'active_tracks': len(self.active_tracks),
            'completed_tracks': len(self.completed_tracks),
            'total_vehicles_seen': self.total_vehicles_seen,
            'speed_stats': self.get_speed_statistics(),
            'direction_stats': self.get_direction_statistics()
        }


class TrajectoryAnalyzer:
    """
    Analyzes vehicle trajectories for traffic pattern insights.
    """

    def __init__(self, tracker: DeepSORTTracker):
        """Initialize analyzer with tracker."""
        self.tracker = tracker

    def detect_stopped_vehicles(self, min_speed_threshold: float = 0.5) -> List[int]:
        """
        Detect vehicles that are essentially stopped.

        Args:
            min_speed_threshold: Speed threshold in m/s

        Returns:
            List of stopped vehicle track IDs
        """
        stopped_vehicles = []

        for track_id, track in self.tracker.active_tracks.items():
            avg_speed = track.get_average_speed()
            if avg_speed is not None and avg_speed < min_speed_threshold:
                stopped_vehicles.append(track_id)

        return stopped_vehicles

    def detect_speeding_vehicles(self, max_speed_threshold: float = 20.0) -> List[int]:
        """
        Detect vehicles exceeding speed limit.

        Args:
            max_speed_threshold: Maximum allowed speed in m/s

        Returns:
            List of speeding vehicle track IDs
        """
        speeding_vehicles = []

        for track_id, track in self.tracker.active_tracks.items():
            current_speed = track.calculate_speed(fps=self.tracker.fps,
                                                pixels_per_meter=self.tracker.pixels_per_meter)
            if current_speed is not None and current_speed > max_speed_threshold:
                speeding_vehicles.append(track_id)

        return speeding_vehicles

    def calculate_congestion_index(self) -> float:
        """
        Calculate traffic congestion index based on vehicle speeds.

        Returns:
            Congestion index [0, 1] where 1 is completely congested
        """
        if not self.tracker.active_tracks:
            return 0.0

        speeds = []
        for track in self.tracker.active_tracks.values():
            avg_speed = track.get_average_speed()
            if avg_speed is not None:
                speeds.append(avg_speed)

        if not speeds:
            return 0.0

        # Normalized average speed (max expected speed: 25 m/s)
        avg_speed = np.mean(speeds)
        congestion = 1.0 - (min(avg_speed, 25.0) / 25.0)

        return min(1.0, max(0.0, congestion))

    def get_flow_direction(self) -> Optional[float]:
        """
        Get dominant traffic flow direction.

        Returns:
            Dominant direction angle in degrees or None
        """
        directions = []

        for track in self.tracker.active_tracks.values():
            avg_dir = track.get_average_direction()
            if avg_dir is not None:
                directions.append(avg_dir)

        if not directions:
            return None

        # Convert to unit vectors for averaging
        directions = np.array(directions) * np.pi / 180
        sin_sum = np.sum(np.sin(directions))
        cos_sum = np.sum(np.cos(directions))

        avg_angle = np.arctan2(sin_sum, cos_sum) * 180 / np.pi
        return (avg_angle + 360) % 360

    def identify_congestion_zones(self, region_grid: Tuple[int, int] = (4, 3)) -> Dict[str, List[int]]:
        """
        Identify congestion in different regions.

        Args:
            region_grid: Grid dimensions for region analysis

        Returns:
            Dictionary mapping region names to track IDs in that region
        """
        regions = {f"zone_{i}_{j}": []
                   for i in range(region_grid[0])
                   for j in range(region_grid[1])}

        for track_id, track in self.tracker.active_tracks.items():
            # Would need frame dimensions to implement properly
            # Placeholder implementation
            pass

        return regions


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initialize tracker
    tracker = DeepSORTTracker(fps=30.0, pixels_per_meter=10.0)

    # Example detection format: ([x1, y1, w, h], confidence, class_id)
    detections = [
        ([100, 100, 50, 100], 0.9, 2),  # car
        ([200, 150, 60, 120], 0.85, 2),  # car
    ]

    # Simulate a dummy frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # Update tracker
    tracks = tracker.update(detections, frame)

    # Print summary
    print(tracker.get_summary())
