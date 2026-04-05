#!/usr/bin/env python3
"""
Red Light Violation Integration System

Integrates red light violation detection with vehicle tracking and signal control.
Provides comprehensive monitoring and reporting for traffic enforcement.
"""

import cv2
import numpy as np
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import json

from .red_light_detector import (
    RedLightViolationDetector,
    IntersectionZoneManager,
    RedLightViolation
)

logger = logging.getLogger(__name__)


class EnforcementSystem:
    """
    Complete red light violation enforcement system.
    Integrates detection, tracking, and reporting.
    """

    def __init__(self,
                 snapshot_dir: str = 'data/violations/snapshots',
                 logs_dir: str = 'data/violations/logs',
                 enable_snapshots: bool = True,
                 enable_logging: bool = True):
        """
        Initialize enforcement system.

        Args:
            snapshot_dir: Directory for violation snapshots
            logs_dir: Directory for violation logs
            enable_snapshots: Enable vehicle snapshot capture
            enable_logging: Enable JSON/CSV logging
        """
        self.zone_manager = IntersectionZoneManager()
        self.detector = RedLightViolationDetector(self.zone_manager, snapshot_dir)

        self.snapshot_dir = Path(snapshot_dir)
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self.enable_snapshots = enable_snapshots
        self.enable_logging = enable_logging

        # Real-time monitoring
        self.violation_queue: List[RedLightViolation] = []
        self.alerts: Dict[str, Dict[str, Any]] = {}

        # Statistics
        self.frame_count = 0
        self.processing_times = []

        logger.info("Initialized EnforcementSystem")

    def configure_intersection(self,
                            lanes: Dict[str, Dict[str, Any]]):
        """
        Configure intersection with lane zones and stop lines.

        Args:
            lanes: Dictionary of lanes {lane_name: {'zone': polygon, 'stop_line': (p1, p2), ...}}
        """
        for lane_name, lane_config in lanes.items():
            # Define tracking zone
            if 'zone' in lane_config:
                self.zone_manager.define_tracking_zone(
                    lane_name,
                    lane_config['zone']
                )

            # Define stop line
            if 'stop_line' in lane_config:
                stop_line = lane_config['stop_line']
                self.zone_manager.define_stop_line(
                    lane_name,
                    stop_line[0],
                    stop_line[1],
                    lane_config.get('crossing_direction', (0, 1))
                )

            # Define position
            if 'position' in lane_config:
                self.zone_manager.define_lane_position(
                    lane_name,
                    lane_config['position']
                )

        logger.info(f"Configured {len(lanes)} lanes for red light monitoring")

    def process_frame(self,
                     frame: np.ndarray,
                     active_tracks: Dict[int, Any],
                     signal_state: Dict[str, str],
                     frame_number: int) -> Dict[str, Any]:
        """
        Process frame for red light violations.

        Args:
            frame: Video frame
            active_tracks: Dictionary of active vehicle tracks
            signal_state: Current signal state {lane: status}
            frame_number: Frame sequence number

        Returns:
            Processing results with violations and statistics
        """
        import time
        start_time = time.time()

        self.frame_count += 1

        # Update signal state
        self.detector.update_signal_state(signal_state)

        # Detect violations
        violations = self.detector.detect_violations(active_tracks, frame, frame_number)

        # Add to queue
        self.violation_queue.extend(violations)

        # Create alerts
        for violation in violations:
            self._create_alert(violation)

        # Calculate processing time
        elapsed = time.time() - start_time
        self.processing_times.append(elapsed)

        results = {
            'frame_number': frame_number,
            'violations_detected': len(violations),
            'total_violations': self.detector.violation_count,
            'processing_time_ms': elapsed * 1000,
            'violations': [v.to_dict() for v in violations],
            'statistics': self.detector.get_statistics()
        }

        return results

    def _create_alert(self, violation: RedLightViolation):
        """Create alert for violation."""
        alert_id = violation.violation_id

        self.alerts[alert_id] = {
            'violation_id': alert_id,
            'track_id': violation.track_id,
            'lane': violation.lane_name,
            'vehicle_class': violation.vehicle_class,
            'timestamp': violation.timestamp,
            'speed': violation.vehicle_speed,
            'snapshot': violation.snapshot_path,
            'severity': self._calculate_severity(violation),
            'status': 'new'
        }

        logger.warning(f"ALERT CREATED: {alert_id}")

    def _calculate_severity(self, violation: RedLightViolation) -> str:
        """
        Calculate violation severity.

        Args:
            violation: RedLightViolation object

        Returns:
            Severity level: 'low', 'medium', 'high', 'critical'
        """
        # High speed increases severity
        if violation.vehicle_speed > 15.0:
            return 'critical'
        elif violation.vehicle_speed > 10.0:
            return 'high'
        elif violation.vehicle_speed > 5.0:
            return 'medium'
        else:
            return 'low'

    def visualize_violations(self,
                            frame: np.ndarray,
                            show_zones: bool = True,
                            show_stats: bool = True) -> np.ndarray:
        """
        Visualize violations on frame.

        Args:
            frame: Input frame
            show_zones: Show tracking zones
            show_stats: Show statistics

        Returns:
            Annotated frame
        """
        annotated = self.detector.draw_violations(
            frame,
            draw_zones=show_zones,
            draw_stats=show_stats
        )

        # Draw alerts
        y_offset = 200
        for alert_id, alert in list(self.alerts.items())[-5:]:  # Show last 5
            color = {
                'low': (255, 255, 0),
                'medium': (0, 165, 255),
                'high': (0, 100, 255),
                'critical': (0, 0, 255)
            }.get(alert['severity'], (255, 255, 0))

            cv2.putText(
                annotated,
                f"ALERT: {alert['vehicle_class']} - {alert['severity'].upper()}",
                (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2
            )
            y_offset += 20

        return annotated

    def get_violation_report(self) -> Dict[str, Any]:
        """Get comprehensive violation report."""
        return {
            'timestamp': datetime.now().isoformat(),
            'total_frames_processed': self.frame_count,
            'total_violations': self.detector.violation_count,
            'violations_by_lane': dict(self.detector.violations_by_lane),
            'violations_by_class': dict(self.detector.violations_by_class),
            'avg_processing_time_ms': (
                np.mean(self.processing_times) * 1000
                if self.processing_times else 0
            ),
            'violations': [v.to_dict() for v in self.detector.violations.values()],
            'alerts': self.alerts
        }

    def get_high_frequency_violators(self, min_violations: int = 3) -> Dict[int, int]:
        """
        Get vehicles with multiple violations.

        Args:
            min_violations: Minimum violation count

        Returns:
            Dictionary {track_id: violation_count}
        """
        violator_counts = {}
        for violation in self.detector.violations.values():
            violator_counts[violation.track_id] = (
                violator_counts.get(violation.track_id, 0) + 1
            )

        return {
            track_id: count for track_id, count in violator_counts.items()
            if count >= min_violations
        }

    def export_violations(self, output_dir: Optional[str] = None):
        """Export violations to files."""
        export_dir = output_dir or str(self.logs_dir)
        self.detector.export_violations(export_dir)
        logger.info(f"Exported violations to {export_dir}")

    def generate_enforcement_report(self) -> str:
        """
        Generate text report for enforcement actions.

        Returns:
            Formatted report string
        """
        report = "\n" + "=" * 80 + "\n"
        report += "RED LIGHT VIOLATION ENFORCEMENT REPORT\n"
        report += "=" * 80 + "\n\n"

        report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"Frames Processed: {self.frame_count}\n"
        report += f"Total Violations: {self.detector.violation_count}\n\n"

        # By lane
        report += "Violations by Lane:\n"
        for lane, count in self.detector.violations_by_lane.items():
            report += f"  {lane}: {count}\n"

        report += "\n"

        # By vehicle class
        report += "Violations by Vehicle Class:\n"
        for vehicle_class, count in self.detector.violations_by_class.items():
            report += f"  {vehicle_class}: {count}\n"

        report += "\n"

        # High frequency violators
        violators = self.get_high_frequency_violators(min_violations=2)
        if violators:
            report += "Repeat Violators:\n"
            for track_id, count in sorted(
                violators.items(), key=lambda x: x[1], reverse=True
            ):
                report += f"  Vehicle {track_id}: {count} violations\n"

        report += "\n"

        # Recent violations
        report += "Recent Violations (Last 10):\n"
        for i, violation in enumerate(
            list(self.detector.violations.values())[-10:], 1
        ):
            report += (
                f"  {i}. [{violation.timestamp}] {violation.vehicle_class} "
                f"on {violation.lane_name} (Speed: {violation.vehicle_speed:.1f} m/s)\n"
            )

        report += "\n" + "=" * 80 + "\n"

        return report

    def reset(self):
        """Reset enforcement system."""
        self.detector.reset()
        self.violation_queue.clear()
        self.alerts.clear()
        self.frame_count = 0
        self.processing_times.clear()
        logger.info("Enforcement system reset")


class RedLightComplianceAnalyzer:
    """
    Analyzes traffic compliance patterns.
    """

    def __init__(self, enforcement_system: EnforcementSystem):
        """Initialize analyzer."""
        self.enforcement_system = enforcement_system

    def get_lane_compliance_rate(self, lane_name: str) -> float:
        """
        Calculate compliance rate for a lane.

        Args:
            lane_name: Lane to analyze

        Returns:
            Compliance rate (0-1, where 1 is 100% compliant)
        """
        total_vehicles = 0
        violating_vehicles = set()

        for violation in self.enforcement_system.detector.get_violations_for_lane(
            lane_name
        ):
            violating_vehicles.add(violation.track_id)

        if not violating_vehicles and total_vehicles == 0:
            return 1.0

        return 1.0 - (len(violating_vehicles) / max(total_vehicles, 1))

    def get_peak_violation_times(self, bin_size: int = 60) -> Dict[int, int]:
        """
        Get violation frequency by time of day.

        Args:
            bin_size: Time bin size in seconds

        Returns:
            Dictionary {time_bin: violation_count}
        """
        bin_counts = {}

        for violation in self.enforcement_system.detector.violations.values():
            time_bin = int(violation.unix_timestamp // bin_size)
            bin_counts[time_bin] = bin_counts.get(time_bin, 0) + 1

        return bin_counts

    def get_vehicle_class_risk(self) -> Dict[str, float]:
        """
        Calculate violation rate by vehicle class.

        Returns:
            Dictionary {vehicle_class: risk_score}
        """
        class_violations = self.enforcement_system.detector.violations_by_class
        total_violations = self.enforcement_system.detector.violation_count

        if total_violations == 0:
            return {}

        return {
            vehicle_class: count / total_violations
            for vehicle_class, count in class_violations.items()
        }

    def generate_compliance_report(self) -> str:
        """Generate compliance analysis report."""
        report = "\n" + "-" * 60 + "\n"
        report += "TRAFFIC COMPLIANCE ANALYSIS\n"
        report += "-" * 60 + "\n\n"

        # Lane compliance
        report += "Lane Compliance Rates:\n"
        for lane_name in self.enforcement_system.zone_manager.tracking_zones.keys():
            compliance = self.get_lane_compliance_rate(lane_name)
            report += f"  {lane_name}: {compliance * 100:.1f}%\n"

        report += "\n"

        # Vehicle class risk
        risk = self.get_vehicle_class_risk()
        if risk:
            report += "Violation Risk by Vehicle Class:\n"
            for vehicle_class, risk_score in sorted(
                risk.items(), key=lambda x: x[1], reverse=True
            ):
                report += f"  {vehicle_class}: {risk_score * 100:.1f}%\n"

        report += "\n" + "-" * 60 + "\n"

        return report


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initialize system
    enforcement = EnforcementSystem()

    # Configure intersection
    lanes = {
        'North': {
            'zone': np.array([
                [300, 0], [400, 0], [400, 200], [300, 200]
            ], dtype=np.float32),
            'stop_line': ((300, 200), (400, 200)),
            'position': (350, 100)
        }
    }

    enforcement.configure_intersection(lanes)

    # Create analyzer
    analyzer = RedLightComplianceAnalyzer(enforcement)

    print(enforcement.generate_enforcement_report())
    print(analyzer.generate_compliance_report())
