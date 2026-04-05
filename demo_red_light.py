#!/usr/bin/env python3
"""
Red Light Violation Detection Demo

Demonstrates the complete red light enforcement system with:
- Real-time violation detection
- Snapshot capture
- Violation logging
- Compliance reporting
"""

import cv2
import numpy as np
import logging
import argparse
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from vision.red_light_integration import EnforcementSystem, RedLightComplianceAnalyzer
from vision.deepsort_tracker import DeepSORTTracker, VehicleTrack

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RedLightEnforcementDemo:
    """
    Demonstration of red light violation detection system.
    """

    def __init__(self, video_source: str = 0, fps: float = 30.0):
        """
        Initialize demo.

        Args:
            video_source: Video file path or camera index
            fps: Frames per second
        """
        self.video_source = video_source
        self.fps = fps

        # Initialize enforcement system
        self.enforcement = EnforcementSystem(
            snapshot_dir='data/violations/snapshots',
            logs_dir='data/violations/logs',
            enable_snapshots=True,
            enable_logging=True
        )

        # Initialize tracker (for demo)
        self.tracker = DeepSORTTracker(fps=fps)

        # Initialize analyzer
        self.analyzer = RedLightComplianceAnalyzer(self.enforcement)

        # Configure demo intersection
        self._configure_demo_intersection()

        logger.info(f"Initialized demo with source: {video_source}")

    def _configure_demo_intersection(self):
        """Configure typical intersection layout."""
        h, w = 480, 640  # Default frame size

        # Define lanes with zones and stop lines
        lanes = {
            'North': {
                'zone': np.array([
                    [w // 2 - 40, 0],
                    [w // 2 + 40, 0],
                    [w // 2 + 40, h // 2 - 60],
                    [w // 2 - 40, h // 2 - 60]
                ], dtype=np.float32),
                'stop_line': (
                    (w // 2 - 40, h // 2 - 60),
                    (w // 2 + 40, h // 2 - 60)
                ),
                'position': (w // 2, h // 4)
            },
            'South': {
                'zone': np.array([
                    [w // 2 - 40, h // 2 + 60],
                    [w // 2 + 40, h // 2 + 60],
                    [w // 2 + 40, h],
                    [w // 2 - 40, h]
                ], dtype=np.float32),
                'stop_line': (
                    (w // 2 - 40, h // 2 + 60),
                    (w // 2 + 40, h // 2 + 60)
                ),
                'position': (w // 2, 3 * h // 4)
            },
            'East': {
                'zone': np.array([
                    [w // 2 + 60, h // 2 - 40],
                    [w, h // 2 - 40],
                    [w, h // 2 + 40],
                    [w // 2 + 60, h // 2 + 40]
                ], dtype=np.float32),
                'stop_line': (
                    (w // 2 + 60, h // 2 - 40),
                    (w // 2 + 60, h // 2 + 40)
                ),
                'position': (3 * w // 4, h // 2)
            },
            'West': {
                'zone': np.array([
                    [0, h // 2 - 40],
                    [w // 2 - 60, h // 2 - 40],
                    [w // 2 - 60, h // 2 + 40],
                    [0, h // 2 + 40]
                ], dtype=np.float32),
                'stop_line': (
                    (w // 2 - 60, h // 2 - 40),
                    (w // 2 - 60, h // 2 + 40)
                ),
                'position': (w // 4, h // 2)
            }
        }

        self.enforcement.configure_intersection(lanes)
        logger.info("Configured demo intersection with 4 lanes")

    def process_video(self,
                     output_path: Optional[str] = None,
                     max_frames: Optional[int] = None,
                     display: bool = True) -> Dict[str, Any]:
        """
        Process video and detect red light violations.

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
            cap = cv2.VideoCapture(
                int(self.video_source)
                if isinstance(self.video_source, str)
                else self.video_source
            )
            fps = self.fps
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480

        if not cap.isOpened():
            logger.error(f"Failed to open video source: {self.video_source}")
            return {'success': False, 'error': 'Failed to open video'}

        # Setup video writer
        out = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        frame_count = 0
        stats = {
            'total_frames': 0,
            'total_violations': 0,
            'lanes_monitored': len(self.enforcement.zone_manager.tracking_zones)
        }

        # Signal state cycling (for demo)
        signal_phases = [
            {'North': 'GREEN', 'South': 'RED', 'East': 'RED', 'West': 'GREEN'},
            {'North': 'YELLOW', 'South': 'RED', 'East': 'RED', 'West': 'YELLOW'},
            {'North': 'RED', 'South': 'RED', 'East': 'GREEN', 'West': 'RED'},
            {'North': 'RED', 'South': 'RED', 'East': 'YELLOW', 'West': 'RED'},
        ]

        signal_phase_idx = 0
        phase_frame_duration = 50  # Frames per phase

        try:
            while True:
                ret, frame = cap.read()

                if not ret:
                    break

                frame_count += 1

                if max_frames and frame_count > max_frames:
                    break

                # Get current signal state
                signal_state = signal_phases[signal_phase_idx]

                # Create demo vehicles/tracks
                demo_tracks = self._generate_demo_vehicles(frame, frame_count)

                # Process with enforcement system
                results = self.enforcement.process_frame(
                    frame,
                    demo_tracks,
                    signal_state,
                    frame_count
                )

                # Visualize
                annotated = self.enforcement.visualize_violations(frame)

                # Add signal state info
                y_offset = height - 100
                cv2.putText(
                    annotated,
                    "Signal Status:",
                    (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2
                )

                for lane, state in signal_state.items():
                    y_offset += 20
                    color = {
                        'GREEN': (0, 255, 0),
                        'YELLOW': (0, 255, 255),
                        'RED': (0, 0, 255)
                    }.get(state, (255, 255, 255))

                    cv2.putText(
                        annotated,
                        f"  {lane}: {state}",
                        (20, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.4,
                        color,
                        1
                    )

                # Write to output
                if out:
                    out.write(annotated)

                # Display
                if display:
                    cv2.imshow("Red Light Violation Detection", annotated)

                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

                # Update statistics
                stats['total_frames'] += 1
                stats['total_violations'] = results['total_violations']

                # Cycle signal phase
                if frame_count % phase_frame_duration == 0:
                    signal_phase_idx = (signal_phase_idx + 1) % len(signal_phases)

                # Logging
                if frame_count % 100 == 0:
                    logger.info(
                        f"Frame {frame_count}: {results['violations_detected']} violations "
                        f"(Total: {results['total_violations']})"
                    )

        except Exception as e:
            logger.error(f"Error processing video: {e}")
            return {'success': False, 'error': str(e)}

        finally:
            cap.release()
            if out:
                out.release()
            cv2.destroyAllWindows()

        stats['success'] = True
        logger.info(f"Video processing completed: {stats}")

        return stats

    def _generate_demo_vehicles(self, frame: np.ndarray, frame_number: int) -> Dict[int, Any]:
        """
        Generate demo vehicles/tracks for testing.

        Args:
            frame: Video frame
            frame_number: Current frame number

        Returns:
            Dictionary of demo tracks
        """
        h, w = frame.shape[:2]
        demo_tracks = {}

        # Vehicle 1: Moving North to South (can run red light)
        y = 50 + frame_number * 2
        if y < h:
            bbox = np.array([w // 2 - 25, y, w // 2 + 25, y + 50])
            track = VehicleTrack(
                track_id=1,
                bbox=bbox,
                confidence=0.95,
                class_id=2,
                frame_id=frame_number,
                timestamp=frame_number / 30.0
            )
            track.add_position(w // 2, y + 25, frame_number / 30.0)
            track.vehicle_class = 'car'
            demo_tracks[1] = track

        # Vehicle 2: Moving East to West (can run red light)
        x = w - 50 - frame_number * 2
        if x > 0:
            bbox = np.array([x, h // 2 - 25, x + 50, h // 2 + 25])
            track = VehicleTrack(
                track_id=2,
                bbox=bbox,
                confidence=0.92,
                class_id=2,
                frame_id=frame_number,
                timestamp=frame_number / 30.0
            )
            track.add_position(x + 25, h // 2, frame_number / 30.0)
            track.vehicle_class = 'car'
            demo_tracks[2] = track

        # Vehicle 3: Stationary (parked)
        bbox = np.array([w // 4 - 25, h // 4, w // 4 + 25, h // 4 + 50])
        track = VehicleTrack(
            track_id=3,
            bbox=bbox,
            confidence=0.88,
            class_id=2,
            frame_id=frame_number,
            timestamp=frame_number / 30.0
        )
        track.add_position(w // 4, h // 4 + 25, frame_number / 30.0)
        track.vehicle_class = 'truck'
        demo_tracks[3] = track

        return demo_tracks

    def print_enforcement_report(self):
        """Print enforcement report."""
        logger.info(self.enforcement.generate_enforcement_report())

    def print_compliance_report(self):
        """Print compliance analysis."""
        logger.info(self.analyzer.generate_compliance_report())

    def export_results(self):
        """Export results to files."""
        self.enforcement.export_violations()
        logger.info("Results exported")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Red Light Violation Detection Demo"
    )
    parser.add_argument("--video", type=str, default="0",
                       help="Video file path or camera index (default: 0)")
    parser.add_argument("--output", type=str, default=None,
                       help="Output video path")
    parser.add_argument("--max-frames", type=int, default=None,
                       help="Maximum frames to process")
    parser.add_argument("--fps", type=float, default=30.0,
                       help="FPS for video processing")
    parser.add_argument("--no-display", action="store_true",
                       help="Don't display video")

    args = parser.parse_args()

    # Initialize and run demo
    demo = RedLightEnforcementDemo(video_source=args.video, fps=args.fps)

    logger.info("Starting Red Light Violation Detection Demo")
    logger.info("Press 'q' to quit")

    stats = demo.process_video(
        output_path=args.output,
        max_frames=args.max_frames,
        display=not args.no_display
    )

    if stats.get('success'):
        demo.print_enforcement_report()
        demo.print_compliance_report()
        demo.export_results()
        logger.info("Demo completed successfully")
    else:
        logger.error(f"Demo failed: {stats.get('error')}")


if __name__ == "__main__":
    main()
