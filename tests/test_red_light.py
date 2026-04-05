#!/usr/bin/env python3
"""
Unit tests for Red Light Violation Detection System

Tests cover:
- IntersectionZoneManager (zone definitions, crossing detection)
- RedLightViolationDetector (violation detection, snapshot saving)
- EnforcementSystem (frame processing, alerts)
- RedLightComplianceAnalyzer (compliance metrics)
"""

import unittest
import tempfile
import json
import csv
import numpy as np
import cv2
import sys
import os
from pathlib import Path
from typing import Dict, Any

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from vision.red_light_detector import (
    IntersectionZoneManager,
    RedLightViolationDetector,
    RedLightViolation
)
from vision.red_light_integration import (
    EnforcementSystem,
    RedLightComplianceAnalyzer
)
from vision.deepsort_tracker import VehicleTrack


class TestIntersectionZoneManager(unittest.TestCase):
    """Test zone definition and crossing detection."""

    def setUp(self):
        """Set up test zone manager."""
        self.zone_manager = IntersectionZoneManager()

    def test_zone_definition(self):
        """Test defining a tracking zone."""
        zone = np.array([
            [100, 100],
            [200, 100],
            [200, 200],
            [100, 200]
        ], dtype=np.float32)

        self.zone_manager.define_tracking_zone('Test', zone)

        self.assertIn('Test', self.zone_manager.tracking_zones)
        np.testing.assert_array_equal(
            self.zone_manager.tracking_zones['Test'],
            zone
        )

    def test_stop_line_definition(self):
        """Test defining a stop line."""
        self.zone_manager.define_stop_line(
            'Test',
            start=(100, 150),
            end=(200, 150)
        )

        self.assertIn('Test', self.zone_manager.stop_lines)
        self.assertEqual(self.zone_manager.stop_lines['Test'],
                        ((100, 150), (200, 150)))

    def test_point_in_zone(self):
        """Test point-in-zone detection."""
        zone = np.array([
            [100, 100],
            [200, 100],
            [200, 200],
            [100, 200]
        ], dtype=np.float32)

        self.zone_manager.define_tracking_zone('Test', zone)

        # Inside
        self.assertTrue(self.zone_manager.is_point_in_zone('Test', 150, 150))

        # Outside
        self.assertFalse(self.zone_manager.is_point_in_zone('Test', 50, 50))

    def test_stop_line_crossing(self):
        """Test stop-line crossing detection."""
        self.zone_manager.define_stop_line(
            'Test',
            start=(100, 100),
            end=(200, 100)
        )

        # Crossing from above to below
        crossed = self.zone_manager.crosses_stop_line(
            'Test',
            prev_pos=(150, 80),
            curr_pos=(150, 120)
        )
        self.assertTrue(crossed)

        # Not crossing
        crossed = self.zone_manager.crosses_stop_line(
            'Test',
            prev_pos=(150, 90),
            curr_pos=(160, 95)
        )
        self.assertFalse(crossed)

    def test_crossing_direction(self):
        """Test crossing direction detection."""
        self.zone_manager.define_stop_line(
            'Test',
            start=(100, 100),
            end=(200, 100)
        )

        # Forward crossing
        direction = self.zone_manager.get_crossing_direction(
            'Test',
            prev_pos=(150, 80),
            curr_pos=(150, 120)
        )
        self.assertIsNotNone(direction)

        # Invalid lane
        direction = self.zone_manager.get_crossing_direction(
            'Invalid',
            prev_pos=(150, 80),
            curr_pos=(150, 120)
        )
        self.assertIsNone(direction)


class TestRedLightViolationDetector(unittest.TestCase):
    """Test violation detection."""

    def setUp(self):
        """Set up test detector."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.tmpdir = tmpdir
            self.detector = RedLightViolationDetector(
                snapshot_dir=tmpdir,
                framerate=30.0
            )

            # Configure zones
            zone = np.array([
                [100, 100],
                [200, 100],
                [200, 200],
                [100, 200]
            ], dtype=np.float32)

            self.detector.zone_manager.define_tracking_zone('Test', zone)
            self.detector.zone_manager.define_stop_line(
                'Test',
                start=(150, 100),
                end=(150, 200)
            )

    def test_violation_object(self):
        """Test RedLightViolation dataclass."""
        violation = RedLightViolation(
            violation_id='v1',
            track_id=42,
            vehicle_class='car',
            lane_name='North',
            timestamp='2026-04-02 12:00:00',
            unix_timestamp=1743800000.0,
            position=(150.0, 150.0),
            vehicle_speed=10.5,
            vehicle_direction=180.0,
            signal_status='RED',
            crossing_confidence=0.95,
            frame_number=100,
            snapshot_path='/path/to/snapshot.jpg'
        )

        self.assertEqual(violation.track_id, 42)
        self.assertEqual(violation.vehicle_class, 'car')
        self.assertEqual(violation.lane_name, 'North')
        self.assertEqual(violation.vehicle_speed, 10.5)

    def test_violation_creation(self):
        """Test violation creation."""
        track = VehicleTrack(
            track_id=1,
            bbox=np.array([125, 125, 175, 175]),
            confidence=0.95,
            class_id=2,
            frame_id=100,
            timestamp=3.33
        )
        track.add_position(150, 150, 3.33)
        track.vehicle_class = 'car'

        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        violation = self.detector.create_violation(
            track=track,
            lane_name='Test',
            frame=frame,
            frame_number=100
        )

        self.assertIsNotNone(violation)
        self.assertEqual(violation.track_id, 1)
        self.assertEqual(violation.lane_name, 'Test')
        self.assertEqual(violation.vehicle_class, 'car')

    def test_get_statistics(self):
        """Test violation statistics."""
        stats = self.detector.get_statistics()

        self.assertEqual(stats['total_violations'], 0)
        self.assertIn('violations_by_lane', stats)
        self.assertIn('violations_by_class', stats)


class TestEnforcementSystem(unittest.TestCase):
    """Test enforcement system."""

    def setUp(self):
        """Set up test enforcement system."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.tmpdir = tmpdir
            self.enforcement = EnforcementSystem(
                snapshot_dir=tmpdir,
                logs_dir=tmpdir,
                enable_snapshots=True,
                enable_logging=True
            )

            # Configure test lane
            self.enforcement.configure_intersection({
                'North': {
                    'zone': np.array([
                        [300, 100],
                        [340, 100],
                        [340, 240],
                        [300, 240]
                    ], dtype=np.float32),
                    'stop_line': ((300, 240), (340, 240)),
                    'position': (320, 170)
                }
            })

    def test_configuration(self):
        """Test intersection configuration."""
        self.assertIn('North', self.enforcement.zone_manager.tracking_zones)
        self.assertIn('North', self.enforcement.zone_manager.stop_lines)

    def test_frame_processing(self):
        """Test frame processing."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        tracks = {}

        signal_state = {'North': 'RED'}

        results = self.enforcement.process_frame(
            frame=frame,
            active_tracks=tracks,
            signal_state=signal_state,
            frame_number=1
        )

        self.assertIn('violations_detected', results)
        self.assertIn('total_violations', results)
        self.assertEqual(results['violations_detected'], 0)

    def test_alert_generation(self):
        """Test alert generation."""
        track = VehicleTrack(
            track_id=1,
            bbox=np.array([310, 150, 330, 170]),
            confidence=0.95,
            class_id=2,
            frame_id=100,
            timestamp=3.33
        )
        track.add_position(320, 165, 3.33)
        track.vehicle_class = 'car'

        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        alert = self.enforcement.create_alert(
            track=track,
            frame=frame,
            frame_number=100,
            lane_name='North'
        )

        self.assertIsNotNone(alert)
        self.assertEqual(alert['status'], 'VIOLATION_DETECTED')
        self.assertEqual(alert['vehicle_type'], 'car')

    def test_severity_calculation(self):
        """Test severity calculation."""
        severities = {
            5.0: 'low',
            7.5: 'medium',
            12.5: 'high',
            15.0: 'critical'
        }

        for speed, expected_severity in severities.items():
            severity = self.enforcement.calculate_severity(speed)
            self.assertEqual(severity, expected_severity)

    def test_visualization(self):
        """Test visualization."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        result = self.enforcement.visualize_violations(frame)

        self.assertIsNotNone(result)
        self.assertEqual(result.shape, frame.shape)

    def test_export_violations(self):
        """Test exporting violations."""
        # Create dummy violation
        self.enforcement.detector.violations.append(
            RedLightViolation(
                violation_id='test_1',
                track_id=1,
                vehicle_class='car',
                lane_name='North',
                timestamp='2026-04-02 12:00:00',
                unix_timestamp=1743800000.0,
                position=(150.0, 150.0),
                vehicle_speed=10.0,
                vehicle_direction=180.0,
                signal_status='RED',
                crossing_confidence=0.95,
                frame_number=100,
                snapshot_path='snapshot.jpg'
            )
        )

        # Export
        json_path, csv_path = self.enforcement.export_violations()

        # Check JSON
        if json_path and Path(json_path).exists():
            with open(json_path, 'r') as f:
                data = json.load(f)
                self.assertGreater(len(data), 0)


class TestRedLightComplianceAnalyzer(unittest.TestCase):
    """Test compliance analysis."""

    def setUp(self):
        """Set up test analyzer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.enforcement = EnforcementSystem(
                snapshot_dir=tmpdir,
                logs_dir=tmpdir
            )

            self.analyzer = RedLightComplianceAnalyzer(self.enforcement)

    def test_lane_compliance_rate(self):
        """Test lane compliance rate calculation."""
        # Add dummy violations
        self.enforcement.detector.violations = [
            RedLightViolation(
                violation_id=f'v{i}',
                track_id=i,
                vehicle_class='car',
                lane_name='North',
                timestamp='2026-04-02 12:00:00',
                unix_timestamp=1743800000.0,
                position=(150.0, 150.0),
                vehicle_speed=10.0,
                vehicle_direction=180.0,
                signal_status='RED',
                crossing_confidence=0.95,
                frame_number=i * 10,
                snapshot_path='snapshot.jpg'
            )
            for i in range(5)
        ]

        report = self.analyzer.generate_compliance_report()

        self.assertIsNotNone(report)
        self.assertIn('Lane Compliance', report)

    def test_vehicle_class_analysis(self):
        """Test vehicle class risk analysis."""
        violations_by_class = self.analyzer.analyze_vehicle_class_risk()

        self.assertIsInstance(violations_by_class, dict)

    def test_repeat_violators(self):
        """Test repeat violator identification."""
        self.enforcement.detector.violations = [
            RedLightViolation(
                violation_id='v1',
                track_id=1,
                vehicle_class='car',
                lane_name='North',
                timestamp='2026-04-02 12:00:00',
                unix_timestamp=1743800000.0,
                position=(150.0, 150.0),
                vehicle_speed=10.0,
                vehicle_direction=180.0,
                signal_status='RED',
                crossing_confidence=0.95,
                frame_number=100,
                snapshot_path='snapshot.jpg'
            ),
            RedLightViolation(
                violation_id='v2',
                track_id=1,
                vehicle_class='car',
                lane_name='North',
                timestamp='2026-04-02 12:01:00',
                unix_timestamp=1743800060.0,
                position=(150.0, 150.0),
                vehicle_speed=10.0,
                vehicle_direction=180.0,
                signal_status='RED',
                crossing_confidence=0.95,
                frame_number=200,
                snapshot_path='snapshot.jpg'
            ),
        ]

        repeat_violators = self.analyzer.identify_repeat_violators()

        self.assertIsInstance(repeat_violators, dict)
        if repeat_violators:
            self.assertIn(1, repeat_violators)


class TestIntegration(unittest.TestCase):
    """Integration tests."""

    def setUp(self):
        """Set up integration test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.tmpdir = tmpdir
            self.enforcement = EnforcementSystem(
                snapshot_dir=tmpdir,
                logs_dir=tmpdir
            )

    def test_end_to_end_workflow(self):
        """Test complete workflow."""
        # Configure intersection
        zones = {
            'North': {
                'zone': np.array([
                    [300, 100],
                    [340, 100],
                    [340, 240],
                    [300, 240]
                ], dtype=np.float32),
                'stop_line': ((300, 240), (340, 240)),
                'position': (320, 170)
            }
        }

        self.enforcement.configure_intersection(zones)

        # Create demo tracks
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        tracks = {}

        # Process frames
        for i in range(10):
            signal_state = {'North': 'RED' if i > 3 else 'GREEN'}
            results = self.enforcement.process_frame(
                frame=frame,
                active_tracks=tracks,
                signal_state=signal_state,
                frame_number=i
            )

            self.assertIsNotNone(results)


if __name__ == '__main__':
    unittest.main()
