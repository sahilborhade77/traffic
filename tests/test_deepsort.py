#!/usr/bin/env python3
"""
Unit tests for DeepSORT tracking implementation.
"""

import unittest
import numpy as np
import cv2
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from vision.deepsort_tracker import VehicleTrack, DeepSORTTracker, TrajectoryAnalyzer
from vision.tracking_integration import VehicleTrackingSystem, DwellTimeMonitor

class TestVehicleTrack(unittest.TestCase):
    """Test VehicleTrack class."""

    def setUp(self):
        """Set up test fixtures."""
        bbox = np.array([100, 100, 150, 200])
        self.track = VehicleTrack(
            track_id=1,
            bbox=bbox,
            confidence=0.9,
            class_id=2,
            frame_id=0,
            timestamp=0.0
        )

    def test_centroid_calculation(self):
        """Test centroid calculation."""
        cx, cy = self.track.get_centroid()
        self.assertAlmostEqual(cx, 125.0)
        self.assertAlmostEqual(cy, 150.0)

    def test_position_history(self):
        """Test position history tracking."""
        self.track.add_position(100.0, 100.0, 0.0)
        self.track.add_position(110.0, 110.0, 1.0)

        self.assertEqual(len(self.track.position_history), 2)

    def test_speed_calculation(self):
        """Test speed calculation."""
        self.track.add_position(0.0, 0.0, 0.0)
        self.track.add_position(10.0, 0.0, 1.0)  # 10 pixels in 1 second

        speed = self.track.calculate_speed(fps=30.0, pixels_per_meter=10.0)

        # 10 pixels / 10 pixels_per_meter = 1 meter in 1 second = 1 m/s
        self.assertAlmostEqual(speed, 1.0, places=1)

    def test_direction_calculation(self):
        """Test direction calculation."""
        self.track.add_position(0.0, 0.0, 0.0)
        self.track.add_position(10.0, 0.0, 1.0)  # Moving right

        direction = self.track.calculate_direction()

        # Moving right = 0 degrees
        self.assertAlmostEqual(direction, 0.0, places=1)

    def test_dwell_time_tracking(self):
        """Test dwell time tracking."""
        self.track.update_dwell_time("zone_a", 5.0)
        self.track.update_dwell_time("zone_a", 3.0)

        self.assertAlmostEqual(self.track.dwell_zones["zone_a"], 8.0)


class TestDeepSORTTracker(unittest.TestCase):
    """Test DeepSORTTracker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.tracker = DeepSORTTracker(fps=30.0, pixels_per_meter=10.0)
        self.frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def test_initialization(self):
        """Test tracker initialization."""
        self.assertEqual(self.tracker.fps, 30.0)
        self.assertEqual(self.tracker.pixels_per_meter, 10.0)
        self.assertEqual(len(self.tracker.active_tracks), 0)

    def test_update_tracks(self):
        """Test track update."""
        detections = [
            ([100, 100, 50, 100], 0.9, 2),
            ([200, 150, 60, 120], 0.85, 2),
        ]

        active_tracks = self.tracker.update(detections, self.frame)

        # Tracks may not be confirmed immediately, so just check it doesn't crash
        self.assertIsInstance(active_tracks, dict)

    def test_get_summary(self):
        """Test summary generation."""
        summary = self.tracker.get_summary()

        self.assertIn('frame_id', summary)
        self.assertIn('active_tracks', summary)
        self.assertIn('completed_tracks', summary)
        self.assertIn('speed_stats', summary)
        self.assertIn('direction_stats', summary)

    def test_speed_statistics(self):
        """Test speed statistics."""
        stats = self.tracker.get_speed_statistics()

        self.assertIn('count', stats)
        self.assertIn('mean', stats)
        self.assertIn('std', stats)


class TestTrajectoryAnalyzer(unittest.TestCase):
    """Test TrajectoryAnalyzer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.tracker = DeepSORTTracker(fps=30.0)
        self.analyzer = TrajectoryAnalyzer(self.tracker)

    def test_detect_stopped_vehicles(self):
        """Test stopped vehicle detection."""
        stopped = self.analyzer.detect_stopped_vehicles()
        self.assertIsInstance(stopped, list)

    def test_detect_speeding_vehicles(self):
        """Test speeding vehicle detection."""
        speeding = self.analyzer.detect_speeding_vehicles()
        self.assertIsInstance(speeding, list)

    def test_congestion_calculation(self):
        """Test congestion index calculation."""
        congestion = self.analyzer.calculate_congestion_index()

        self.assertGreaterEqual(congestion, 0.0)
        self.assertLessEqual(congestion, 1.0)


class TestVehicleTrackingSystem(unittest.TestCase):
    """Test VehicleTrackingSystem integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.system = VehicleTrackingSystem(fps=30.0)
        self.frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def test_initialization(self):
        """Test system initialization."""
        self.assertEqual(self.system.fps, 30.0)
        self.assertIsNotNone(self.system.tracker)
        self.assertIsNotNone(self.system.analyzer)

    def test_process_frame(self):
        """Test frame processing."""
        detections = [([100, 100, 50, 100], 0.9, 2)]
        results = self.system.process_frame(self.frame, detections)

        self.assertIn('frame_id', results)
        self.assertIn('active_tracks', results)
        self.assertIn('statistics', results)

    def test_visualization(self):
        """Test track visualization."""
        detections = [([100, 100, 50, 100], 0.9, 2)]
        self.system.process_frame(self.frame, detections)

        annotated = self.system.visualize_tracks(self.frame)

        self.assertEqual(annotated.shape, self.frame.shape)


class TestDwellTimeMonitor(unittest.TestCase):
    """Test DwellTimeMonitor."""

    def setUp(self):
        """Set up test fixtures."""
        self.tracker = DeepSORTTracker()
        self.monitor = DwellTimeMonitor(self.tracker)

    def test_zone_definition(self):
        """Test zone definition."""
        zone = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.float32)
        self.monitor.define_zone("test_zone", zone)

        self.assertIn("test_zone", self.monitor.zone_definitions)

    def test_point_in_zone(self):
        """Test point in zone detection."""
        zone = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.float32)
        self.monitor.define_zone("test_zone", zone)

        # Point inside zone
        self.assertTrue(self.monitor.check_point_in_zone((50, 50), "test_zone"))

        # Point outside zone
        self.assertFalse(self.monitor.check_point_in_zone((150, 150), "test_zone"))

    def test_dwell_report(self):
        """Test dwell report generation."""
        zone = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.float32)
        self.monitor.define_zone("test_zone", zone)

        report = self.monitor.get_dwell_report()

        self.assertIn("test_zone", report)
        self.assertIsInstance(report["test_zone"], dict)


def run_tests():
    """Run all tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    run_tests()
