#!/usr/bin/env python3
"""
DeepSORT Vehicle Tracking Demo

Demonstrates real-time vehicle tracking with speed, direction, and dwell time monitoring.
Works with video files or camera input.
"""

import cv2
import numpy as np
import logging
import argparse
from pathlib import Path
import sys
import os
from typing import Dict, Any, List, Tuple, Optional

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from vision.deepsort_tracker import DeepSORTTracker, TrajectoryAnalyzer
from vision.tracking_integration import VehicleTrackingSystem, DwellTimeMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VehicleTrackingDemo:
    """
    Demonstration of DeepSORT vehicle tracking system.
    """

    def __init__(self, video_source: str = 0, fps: float = 30.0):
        """
        Initialize demo.

        Args:
            video_source: Video file path or camera index
            fps: Frames per second (for file, this is read from video)
        """
        self.video_source = video_source
        self.fps = fps

        # Initialize tracking system
        self.tracking_system = VehicleTrackingSystem(
            fps=fps,
            pixels_per_meter=10.0,
            enable_analytics=True
        )

        # Initialize dwell time monitor
        self.dwell_monitor = DwellTimeMonitor(self.tracking_system.tracker)

        # Define example zones for dwell time
        self._define_example_zones()

        logger.info(f"Initialized tracking demo with source: {video_source}")

    def _define_example_zones(self):
        """Define example parking/congestion zones."""
        # Zone 1: Center region (for demo purposes)
        zone1 = np.array([
            [200, 150],
            [450, 150],
            [450, 350],
            [200, 350]
        ], dtype=np.float32)

        self.dwell_monitor.define_zone("center_zone", zone1)

    def process_video(self,
                     output_path: Optional[str] = None,
                     max_frames: Optional[int] = None,
                     display: bool = True) -> Dict[str, Any]:
        """
        Process video and track vehicles.

        Args:
            output_path: Path to save output video (optional)
            max_frames: Maximum frames to process (optional)
            display: Whether to display processed frames

        Returns:
            Processing summary
        """
        logger.info(f"Starting video processing from {self.video_source}")

        # Open video
        if isinstance(self.video_source, str) and Path(self.video_source).exists():
            cap = cv2.VideoCapture(self.video_source)
            fps = cap.get(cv2.CAP_PROP_FPS) or self.fps
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        else:
            cap = cv2.VideoCapture(int(self.video_source) if isinstance(self.video_source, str) else self.video_source)
            fps = self.fps
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480

        if not cap.isOpened():
            logger.error(f"Failed to open video source: {self.video_source}")
            return {'success': False, 'error': 'Failed to open video'}

        # Setup video writer if output path provided
        out = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        frame_count = 0
        stats = {
            'total_frames': 0,
            'total_vehicles_tracked': 0,
            'avg_active_tracks': 0,
            'peak_active_tracks': 0
        }

        try:
            while True:
                ret, frame = cap.read()

                if not ret:
                    break

                frame_count += 1

                if max_frames and frame_count > max_frames:
                    break

                # Generate dummy detections for demo
                # In real use, these would come from YOLO detector
                detections = self._generate_dummy_detections(frame)

                # Process frame with tracking
                results = self.tracking_system.process_frame(frame, detections)

                # Update dwell times
                time_delta = 1.0 / fps
                self.dwell_monitor.update_dwell_times(time_delta)

                # Visualize
                annotated = self.tracking_system.visualize_tracks(frame)
                annotated = self.dwell_monitor.draw_zones(annotated)

                # Draw dwell information
                dwell_report = self.dwell_monitor.get_dwell_report()
                y_offset = 100
                for zone_name, vehicles in dwell_report.items():
                    if vehicles:
                        cv2.putText(annotated, f"{zone_name}: {len(vehicles)} vehicles",
                                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
                        y_offset += 25

                # Write to output if provided
                if out:
                    out.write(annotated)

                # Display
                if display:
                    cv2.imshow("DeepSORT Vehicle Tracking", annotated)

                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

                # Update statistics
                stats['total_frames'] += 1
                num_active = len(results['active_tracks'])
                stats['avg_active_tracks'] += num_active
                stats['peak_active_tracks'] = max(stats['peak_active_tracks'], num_active)

                # Logging
                if frame_count % 30 == 0:
                    logger.info(f"Frame {frame_count}: {num_active} active tracks")

        except Exception as e:
            logger.error(f"Error processing video: {e}")
            return {'success': False, 'error': str(e)}

        finally:
            cap.release()
            if out:
                out.release()
            cv2.destroyAllWindows()

        # Calculate final statistics
        if stats['total_frames'] > 0:
            stats['avg_active_tracks'] /= stats['total_frames']

        stats['success'] = True
        logger.info(f"Video processing completed: {stats}")

        return stats

    def _generate_dummy_detections(self, frame: np.ndarray) -> List[Tuple]:
        """
        Generate dummy detections for demonstration.
        In real use, this would come from YOLO detector.

        Args:
            frame: Input frame

        Returns:
            List of detections
        """
        h, w = frame.shape[:2]

        # Create moving objects for demo
        frame_id = self.tracking_system.tracker.frame_id

        detections = []

        # Object 1: Moving left to right
        x1 = 100 + frame_id * 5
        if x1 < w:
            detections.append((
                [max(0, x1), 150, 50, 100],  # [x1, y1, w, h]
                0.9,  # confidence
                2  # class_id (car)
            ))

        # Object 2: Moving down
        y1 = 100 + frame_id * 3
        if y1 < h:
            detections.append((
                [300, max(0, y1), 60, 120],
                0.85,
                2
            ))

        # Object 3: Stationary (parked)
        detections.append((
            [500, 250, 55, 110],
            0.88,
            2
        ))

        return detections

    def print_tracking_report(self):
        """Print detailed tracking report."""
        logger.info("=== TRACKING REPORT ===")

        all_tracks = self.tracking_system.get_all_tracks_report()

        logger.info(f"Active Tracks: {len(all_tracks['active_tracks'])}")
        for track in all_tracks['active_tracks']:
            if track:
                logger.info(f"\nTrack ID {track['track_id']}:")
                logger.info(f"  Class: {track['vehicle_class']}")
                logger.info(f"  Speed: {track['metrics']['current_speed_ms']:.2f} m/s (avg: {track['metrics']['average_speed_ms']:.2f} m/s)")
                logger.info(f"  Direction: {track['metrics']['current_direction_deg']:.1f}°")
                logger.info(f"  Dwell Times: {track['dwell_times']}")

        logger.info(f"\nCompleted Tracks: {len(all_tracks['completed_tracks'])}")

        # Print summary from tracker
        summary = self.tracking_system.tracker.get_summary()
        logger.info(f"\nSummary:")
        logger.info(f"  Total Vehicles Seen: {summary['total_vehicles_seen']}")
        logger.info(f"  Speed Stats: {summary['speed_stats']}")
        logger.info(f"  Direction Stats: {summary['direction_stats']}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="DeepSORT Vehicle Tracking Demo")
    parser.add_argument("--video", type=str, default="0", help="Video file path or camera index (default: 0)")
    parser.add_argument("--output", type=str, default=None, help="Output video path")
    parser.add_argument("--max-frames", type=int, default=None, help="Maximum frames to process")
    parser.add_argument("--fps", type=float, default=30.0, help="FPS for video processing")
    parser.add_argument("--no-display", action="store_true", help="Don't display video")

    args = parser.parse_args()

    # Initialize and run demo
    demo = VehicleTrackingDemo(video_source=args.video, fps=args.fps)

    logger.info("Starting DeepSORT Vehicle Tracking Demo")
    logger.info("Press 'q' to quit")

    stats = demo.process_video(
        output_path=args.output,
        max_frames=args.max_frames,
        display=not args.no_display
    )

    if stats.get('success'):
        demo.print_tracking_report()
        logger.info("Demo completed successfully")
    else:
        logger.error(f"Demo failed: {stats.get('error')}")


if __name__ == "__main__":
    main()
