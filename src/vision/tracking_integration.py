#!/usr/bin/env python3
"""
DeepSORT Vehicle Tracking Integration

Integrates DeepSORT tracking with YOLO detection for complete vehicle monitoring system.
Provides real-time speed, direction, and dwell time calculations.
"""

import cv2
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
from pathlib import Path
import json

from .deepsort_tracker import DeepSORTTracker, TrajectoryAnalyzer, VehicleTrack

logger = logging.getLogger(__name__)

class VehicleTrackingSystem:
    """
    Complete vehicle tracking system combining YOLO detection and DeepSORT tracking.
    """

    def __init__(self,
                 fps: float = 30.0,
                 pixels_per_meter: float = 10.0,
                 max_age: int = 30,
                 enable_analytics: bool = True):
        """
        Initialize tracking system.

        Args:
            fps: Video frames per second
            pixels_per_meter: Calibration for distance measurement
            max_age: Maximum frames to keep lost track
            enable_analytics: Enable trajectory analysis
        """
        self.tracker = DeepSORTTracker(
            fps=fps,
            pixels_per_meter=pixels_per_meter,
            max_age=max_age
        )

        self.analyzer = TrajectoryAnalyzer(self.tracker) if enable_analytics else None
        self.fps = fps

        # Data logging
        self.tracking_logs: List[Dict[str, Any]] = []
        self.enable_logging = True

        logger.info("Initialized VehicleTrackingSystem")

    def process_frame(self,
                     frame: np.ndarray,
                     detections: List[Tuple[List[float], float, int]],
                     visualization_params: Optional[Dict[str, bool]] = None) -> Dict[str, Any]:
        """
        Process a frame with detections and return tracking results.

        Args:
            frame: Input video frame
            detections: List of ([x1, y1, w, h], confidence, class_id) tuples
            visualization_params: Parameters for visualization

        Returns:
            Dictionary with tracking results
        """
        # Update tracker
        active_tracks = self.tracker.update(detections, frame)

        # Prepare results
        results = {
            'frame_id': self.tracker.frame_id,
            'timestamp': cv2.getTickCount() / cv2.getTickFrequency(),
            'active_tracks': {},
            'statistics': {}
        }

        # Extract detailed track information
        for track_id, track in active_tracks.items():
            track_info = self.tracker.get_track_info(track_id)
            if track_info:
                results['active_tracks'][track_id] = track_info

        # Add analytics if enabled
        if self.analyzer:
            results['statistics'] = {
                'speed': self.tracker.get_speed_statistics(),
                'direction': self.tracker.get_direction_statistics(),
                'stopped_vehicles': self.analyzer.detect_stopped_vehicles(),
                'speeding_vehicles': self.analyzer.detect_speeding_vehicles(max_speed_threshold=20.0),
                'congestion_index': self.analyzer.calculate_congestion_index(),
                'flow_direction': self.analyzer.get_flow_direction()
            }

        # Log if enabled
        if self.enable_logging:
            self._log_frame_data(results)

        return results

    def _log_frame_data(self, frame_results: Dict[str, Any]):
        """Log frame tracking data."""
        log_entry = {
            'frame_id': frame_results['frame_id'],
            'timestamp': frame_results['timestamp'],
            'num_active_tracks': len(frame_results['active_tracks']),
            'statistics': frame_results.get('statistics', {})
        }
        self.tracking_logs.append(log_entry)

    def visualize_tracks(self,
                        frame: np.ndarray,
                        draw_trails: bool = True,
                        draw_speed: bool = True,
                        draw_direction: bool = True,
                        draw_zone_info: bool = False) -> np.ndarray:
        """
        Visualize tracking results on frame.

        Args:
            frame: Input frame
            draw_trails: Draw vehicle movement trails
            draw_speed: Draw speed values
            draw_direction: Draw direction arrows
            draw_zone_info: Draw zone/dwell information

        Returns:
            Annotated frame
        """
        annotated = self.tracker.draw_tracks(
            frame,
            draw_trails=draw_trails,
            draw_speed=draw_speed,
            draw_direction=draw_direction
        )

        # Add summary statistics at top
        summary = self.tracker.get_summary()
        cv2.putText(annotated, f"Vehicles: {summary['active_tracks']} | FPS: {self.fps:.0f}",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        if self.analyzer:
            congestion = self.analyzer.calculate_congestion_index()
            flow_dir = self.analyzer.get_flow_direction()
            cv2.putText(annotated, f"Congestion: {congestion:.2f} | Flow: {flow_dir:.0f}° if flow_dir else 'N/A'",
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

        return annotated

    def get_detailed_track_report(self, track_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed report for a specific track.

        Args:
            track_id: ID of track to report on

        Returns:
            Detailed track information
        """
        track = (self.tracker.active_tracks.get(track_id) or
                 self.tracker.completed_tracks.get(track_id))

        if track is None:
            return None

        return {
            'track_id': track_id,
            'status': 'active' if track_id in self.tracker.active_tracks else 'completed',
            'vehicle_class': self.tracker.vehicle_class_map.get(track.class_id, 'unknown'),
            'metrics': {
                'current_speed_ms': track.calculate_speed(fps=self.fps, pixels_per_meter=self.tracker.pixels_per_meter),
                'average_speed_ms': track.get_average_speed(),
                'max_speed_ms': max(track.speed_history) if track.speed_history else None,
                'min_speed_ms': min(track.speed_history) if track.speed_history else None,
                'current_direction_deg': track.calculate_direction(),
                'average_direction_deg': track.get_average_direction(),
                'frames_tracked': track.frame_id,
                'frames_in_view': len(track.position_history)
            },
            'dwell_times': dict(track.dwell_zones),
            'centroid': track.centroid_position,
            'bounding_box': track.bbox.tolist()
        }

    def get_all_tracks_report(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get report for all tracks."""
        return {
            'active_tracks': [
                self.get_detailed_track_report(track_id)
                for track_id in self.tracker.active_tracks.keys()
            ],
            'completed_tracks': [
                self.get_detailed_track_report(track_id)
                for track_id in self.tracker.completed_tracks.keys()
            ]
        }

    def export_tracking_data(self, output_path: str):
        """
        Export tracking data to CSV and JSON.

        Args:
            output_path: Directory to save exported data
        """
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Export logs as CSV
        if self.tracking_logs:
            logs_df = pd.DataFrame(self.tracking_logs)
            logs_df.to_csv(output_dir / 'tracking_logs.csv', index=False)
            logger.info(f"Exported tracking logs to {output_dir / 'tracking_logs.csv'}")

        # Export detailed track information
        all_tracks = self.get_all_tracks_report()

        with open(output_dir / 'detailed_tracks.json', 'w') as f:
            # Convert to JSON-serializable format
            summary = self.tracker.get_summary()
            json_data = {
                'active_tracks': all_tracks['active_tracks'],
                'completed_tracks': all_tracks['completed_tracks'],
                'summary': summary
            }
            json.dump(json_data, f, indent=2, default=str)
            logger.info(f"Exported detailed tracks to {output_dir / 'detailed_tracks.json'}")

    def reset(self):
        """Reset tracking system."""
        self.tracker.reset()
        self.tracking_logs.clear()
        logger.info("Tracking system reset")


class DwellTimeMonitor:
    """
    Specialized monitor for vehicle dwell times in specific zones.
    """

    def __init__(self, tracker: DeepSORTTracker):
        """Initialize dwell time monitor."""
        self.tracker = tracker
        self.zone_definitions: Dict[str, np.ndarray] = {}  # zone_name -> polygon
        self.dwell_records: Dict[int, Dict[str, float]] = {}  # track_id -> {zone_name: time}

    def define_zone(self, zone_name: str, polygon: np.ndarray):
        """
        Define a zone as a polygon.

        Args:
            zone_name: Name of the zone
            polygon: Polygon points as (N, 2) array
        """
        self.zone_definitions[zone_name] = polygon
        logger.info(f"Defined zone: {zone_name}")

    def check_point_in_zone(self, point: Tuple[float, float], zone_name: str) -> bool:
        """
        Check if point is inside a zone.

        Args:
            point: (x, y) coordinate
            zone_name: Zone to check

        Returns:
            True if point is in zone
        """
        if zone_name not in self.zone_definitions:
            return False

        polygon = self.zone_definitions[zone_name]
        result = cv2.pointPolygonTest(polygon.astype(np.int32), point, False)
        return result >= 0

    def update_dwell_times(self, time_delta: float):
        """
        Update dwell times for all active tracks.

        Args:
            time_delta: Time elapsed since last frame (seconds)
        """
        for track_id, track in self.tracker.active_tracks.items():
            if track.centroid_position is None:
                continue

            for zone_name in self.zone_definitions.keys():
                if self.check_point_in_zone(track.centroid_position, zone_name):
                    track.update_dwell_time(zone_name, time_delta)

    def get_dwell_report(self) -> Dict[str, Dict[int, float]]:
        """
        Get dwell time report.

        Returns:
            Dictionary {zone_name: {track_id: dwell_time}}
        """
        report = {zone: {} for zone in self.zone_definitions.keys()}

        for track_id, track in self.tracker.active_tracks.items():
            for zone_name, dwell_time in track.dwell_zones.items():
                if dwell_time > 0:
                    report[zone_name][track_id] = dwell_time

        return report

    def draw_zones(self, frame: np.ndarray, alpha: float = 0.3) -> np.ndarray:
        """
        Draw zone definitions on frame.

        Args:
            frame: Input frame
            alpha: Transparency level

        Returns:
            Frame with drawn zones
        """
        overlay = frame.copy()

        for zone_name, polygon in self.zone_definitions.items():
            # Draw filled polygon
            cv2.polylines(overlay, [polygon.astype(np.int32)], True, (0, 255, 255), 2)

            # Draw zone label
            if len(polygon) > 0:
                label_pos = tuple(polygon[0].astype(int))
                cv2.putText(overlay, zone_name, label_pos,
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        # Blend with original frame
        result = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

        return result


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initialize system
    tracking_system = VehicleTrackingSystem(fps=30.0, pixels_per_meter=10.0)

    # Example frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # Example detections
    detections = [
        ([100, 100, 50, 100], 0.9, 2),
        ([200, 150, 60, 120], 0.85, 2),
    ]

    # Process frame
    results = tracking_system.process_frame(frame, detections)
    print("Tracking Results:", results)

    # Visualize
    annotated = tracking_system.visualize_tracks(frame)
    cv2.imshow("Tracked Vehicles", annotated)
