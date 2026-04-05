#!/usr/bin/env python3
"""
Traffic Data Aggregation Module

Generates hourly and daily statistics:
- Total vehicle counts
- Average wait times
- Peak hour identification
- Violation statistics
- Lane-specific analytics
"""

import json
import csv
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict, field
from collections import defaultdict, deque
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class VehicleMetrics:
    """Vehicle counting and classification metrics."""
    timestamp: str
    lane: str
    vehicle_class: str
    count: int = 1
    avg_speed: float = 0.0
    total_distance: float = 0.0


@dataclass
class WaitTimeMetrics:
    """Wait time statistics."""
    timestamp: str
    lane: str
    wait_time_seconds: float
    vehicle_type: str
    vehicle_id: int


@dataclass
class HourlyStatistics:
    """Aggregated hourly statistics."""
    datetime: str
    hour: int
    lane: str
    total_vehicles: int = 0
    vehicle_breakdown: Dict[str, int] = field(default_factory=dict)
    avg_wait_time: float = 0.0
    max_wait_time: float = 0.0
    min_wait_time: float = 0.0
    total_violations: int = 0
    peak_hour: bool = False
    avg_vehicle_speed: float = 0.0
    traffic_density: float = 0.0  # 0-1 scale
    congestion_level: str = 'low'  # low, medium, high, critical


@dataclass
class DailyStatistics:
    """Aggregated daily statistics."""
    date: str
    day_of_week: str
    total_vehicles: int = 0
    vehicle_breakdown: Dict[str, int] = field(default_factory=dict)
    avg_wait_time: float = 0.0
    peak_hours: List[int] = field(default_factory=list)
    total_violations: int = 0
    lanes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    avg_traffic_density: float = 0.0
    busiest_hour: Optional[int] = None
    avg_vehicle_speed: float = 0.0


class TrafficDataAggregator:
    """
    Aggregates real-time traffic data into hourly and daily statistics.
    """

    def __init__(self, data_dir: str = 'data', history_size: int = 3600):
        """
        Initialize data aggregator.

        Args:
            data_dir: Directory for storing aggregated data
            history_size: Number of recent records to maintain in memory
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Statistics directories
        self.stats_dir = self.data_dir / 'statistics'
        self.stats_dir.mkdir(exist_ok=True)

        self.hourly_dir = self.stats_dir / 'hourly'
        self.hourly_dir.mkdir(exist_ok=True)

        self.daily_dir = self.stats_dir / 'daily'
        self.daily_dir.mkdir(exist_ok=True)

        # In-memory buffers (rolling window for current hour)
        self.vehicle_buffer = deque(maxlen=history_size)
        self.wait_time_buffer = deque(maxlen=history_size)
        self.violation_buffer = deque(maxlen=history_size)

        # Current hour aggregations
        self.current_hour_data: Dict[str, Any] = {}
        self.current_day_data: Dict[str, Any] = {}

        # Historical data
        self.hourly_stats: Dict[str, HourlyStatistics] = {}
        self.daily_stats: Dict[str, DailyStatistics] = {}

        # Tracking state
        self.last_aggregation_time = datetime.now()
        self.current_hour = datetime.now().hour
        self.current_date = datetime.now().date().isoformat()

        logger.info("Traffic Data Aggregator initialized")

    def add_vehicle_observation(self, lane: str, vehicle_class: str,
                               speed: float = 0.0, distance: float = 0.0):
        """
        Record a vehicle observation.

        Args:
            lane: Lane identifier
            vehicle_class: Vehicle type (car, truck, motorcycle, etc.)
            speed: Vehicle speed in m/s
            distance: Distance traveled in meters
        """
        metrics = VehicleMetrics(
            timestamp=datetime.now().isoformat(),
            lane=lane,
            vehicle_class=vehicle_class,
            avg_speed=speed,
            total_distance=distance
        )
        self.vehicle_buffer.append(metrics)

    def add_wait_time_observation(self, lane: str, wait_time: float,
                                 vehicle_type: str, vehicle_id: int):
        """
        Record a vehicle wait time.

        Args:
            lane: Lane identifier
            wait_time: Wait time in seconds
            vehicle_type: Vehicle class
            vehicle_id: Unique vehicle identifier
        """
        metrics = WaitTimeMetrics(
            timestamp=datetime.now().isoformat(),
            lane=lane,
            wait_time_seconds=wait_time,
            vehicle_type=vehicle_type,
            vehicle_id=vehicle_id
        )
        self.wait_time_buffer.append(metrics)

    def record_violation(self, lane: str, violation_type: str,
                        vehicle_id: int, severity: str = 'medium'):
        """
        Record a traffic violation.

        Args:
            lane: Lane where violation occurred
            violation_type: Type of violation (red_light, speeding, etc.)
            vehicle_id: Vehicle identifier
            severity: Violation severity
        """
        violation = {
            'timestamp': datetime.now().isoformat(),
            'lane': lane,
            'type': violation_type,
            'vehicle_id': vehicle_id,
            'severity': severity
        }
        self.violation_buffer.append(violation)

    def get_hourly_statistics(self, lane: Optional[str] = None) -> Dict[str, HourlyStatistics]:
        """
        Get current hour's aggregated statistics.

        Args:
            lane: Optional lane filter

        Returns:
            Dictionary of hourly statistics by lane
        """
        now = datetime.now()
        current_hour = now.hour

        # Check if we need to rotate to a new hour
        if current_hour != self.current_hour:
            self._rotate_hour()
            self.current_hour = current_hour

        stats = {}

        # Group vehicle data by lane
        vehicle_by_lane = defaultdict(list)
        for vehicle in self.vehicle_buffer:
            hour_check = datetime.fromisoformat(
                vehicle.timestamp).hour
            if hour_check == current_hour:
                vehicle_by_lane[vehicle.lane].append(vehicle)

        # Group wait times by lane
        wait_by_lane = defaultdict(list)
        for wait_rec in self.wait_time_buffer:
            hour_check = datetime.fromisoformat(wait_rec.timestamp).hour
            if hour_check == current_hour:
                wait_by_lane[wait_rec.lane].append(wait_rec)

        # Group violations by lane
        violations_by_lane = defaultdict(list)
        for violation in self.violation_buffer:
            hour_check = datetime.fromisoformat(
                violation['timestamp']).hour
            if hour_check == current_hour:
                violations_by_lane[violation['lane']].append(violation)

        # Calculate stats per lane
        lanes_to_process = [lane] if lane else list(
            set(list(vehicle_by_lane.keys()) + list(wait_by_lane.keys()))
        )

        for current_lane in lanes_to_process:
            vehicles = vehicle_by_lane.get(current_lane, [])
            waits = wait_by_lane.get(current_lane, [])
            violations = violations_by_lane.get(current_lane, [])

            # Vehicle breakdown
            vehicle_breakdown = defaultdict(int)
            for vehicle in vehicles:
                vehicle_breakdown[vehicle.vehicle_class] += 1

            # Wait time statistics
            wait_times = [w.wait_time_seconds for w in waits]
            avg_wait = np.mean(wait_times) if wait_times else 0.0
            max_wait = np.max(wait_times) if wait_times else 0.0
            min_wait = np.min(wait_times) if wait_times else 0.0

            # Speed statistics
            speeds = [v.avg_speed for v in vehicles if v.avg_speed > 0]
            avg_speed = np.mean(speeds) if speeds else 0.0

            # Congestion level
            total_vehicles = len(vehicles)
            density = min(total_vehicles / 100, 1.0)  # Normalize to 0-1
            if density < 0.3:
                congestion = 'low'
            elif density < 0.6:
                congestion = 'medium'
            elif density < 0.85:
                congestion = 'high'
            else:
                congestion = 'critical'

            hourly_stat = HourlyStatistics(
                datetime=now.isoformat(),
                hour=current_hour,
                lane=current_lane,
                total_vehicles=total_vehicles,
                vehicle_breakdown=dict(vehicle_breakdown),
                avg_wait_time=avg_wait,
                max_wait_time=max_wait,
                min_wait_time=min_wait,
                total_violations=len(violations),
                peak_hour=False,  # Will be calculated in daily aggregation
                avg_vehicle_speed=avg_speed,
                traffic_density=density,
                congestion_level=congestion
            )

            stats[current_lane] = hourly_stat

        return stats

    def get_daily_statistics(self, date: Optional[str] = None) -> DailyStatistics:
        """
        Get aggregated daily statistics.

        Args:
            date: Optional date string (YYYY-MM-DD). Defaults to today.

        Returns:
            Daily statistics object
        """
        target_date = date or datetime.now().date().isoformat()

        # If requesting today but it exists in cache, skip recalculation
        if target_date in self.daily_stats:
            return self.daily_stats[target_date]

        target_dt = datetime.fromisoformat(target_date)
        day_of_week = target_dt.strftime('%A')

        # Collect data for the day
        daily_vehicles = []
        daily_waits = []
        daily_violations = []
        hourly_vehicle_counts = defaultdict(int)
        hourly_violations = defaultdict(int)

        for vehicle in self.vehicle_buffer:
            v_date = datetime.fromisoformat(vehicle.timestamp).date()
            if v_date.isoformat() == target_date:
                daily_vehicles.append(vehicle)
                hour = datetime.fromisoformat(vehicle.timestamp).hour
                hourly_vehicle_counts[hour] += 1

        for wait in self.wait_time_buffer:
            w_date = datetime.fromisoformat(wait.timestamp).date()
            if w_date.isoformat() == target_date:
                daily_waits.append(wait)

        for violation in self.violation_buffer:
            v_date = datetime.fromisoformat(violation['timestamp']).date()
            if v_date.isoformat() == target_date:
                daily_violations.append(violation)
                hour = datetime.fromisoformat(violation['timestamp']).hour
                hourly_violations[hour] += 1

        # Vehicle breakdown
        vehicle_breakdown = defaultdict(int)
        for vehicle in daily_vehicles:
            vehicle_breakdown[vehicle.vehicle_class] += 1

        # Wait time statistics
        wait_times = [w.wait_time_seconds for w in daily_waits]
        avg_wait = np.mean(wait_times) if wait_times else 0.0

        # Identify peak hours (top 3 hours by volume)
        peak_hours = sorted(
            hourly_vehicle_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        peak_hour_list = [h[0] for h in peak_hours]
        busiest_hour = peak_hour_list[0] if peak_hour_list else None

        # Speed statistics
        speeds = [v.avg_speed for v in daily_vehicles if v.avg_speed > 0]
        avg_speed = np.mean(speeds) if speeds else 0.0

        # Density calculation
        total_vehicles = len(daily_vehicles)
        avg_density = total_vehicles / (24 * 100)  # Average over 24 hours
        avg_density = min(avg_density, 1.0)

        # Lane-wise breakdown
        lane_data = defaultdict(lambda: {
            'vehicles': 0,
            'violations': 0,
            'avg_wait_time': 0.0
        })

        for vehicle in daily_vehicles:
            lane_data[vehicle.lane]['vehicles'] += 1

        for wait in daily_waits:
            lane_stats = lane_data[wait.lane]
            current_count = lane_stats.get('wait_time_count', 0)
            current_total = lane_stats.get('wait_time_total', 0.0)
            lane_stats['wait_time_total'] = current_total + wait.wait_time_seconds
            lane_stats['wait_time_count'] = current_count + 1
            if lane_stats['wait_time_count'] > 0:
                lane_stats['avg_wait_time'] = (
                    lane_stats['wait_time_total'] / lane_stats['wait_time_count']
                )

        for violation in daily_violations:
            lane_data[violation['lane']]['violations'] += 1

        # Clean up lane data
        for lane in lane_data:
            lane_data[lane].pop('wait_time_total', None)
            lane_data[lane].pop('wait_time_count', None)

        daily_stat = DailyStatistics(
            date=target_date,
            day_of_week=day_of_week,
            total_vehicles=total_vehicles,
            vehicle_breakdown=dict(vehicle_breakdown),
            avg_wait_time=avg_wait,
            peak_hours=peak_hour_list,
            total_violations=len(daily_violations),
            lanes=dict(lane_data),
            avg_traffic_density=avg_density,
            busiest_hour=busiest_hour,
            avg_vehicle_speed=avg_speed
        )

        self.daily_stats[target_date] = daily_stat
        return daily_stat

    def _rotate_hour(self):
        """Save current hour statistics and reset buffers."""
        try:
            now = datetime.now()
            hour_key = now.replace(minute=0, second=0, microsecond=0).isoformat()

            hourly_stats = self.get_hourly_statistics()

            # Save to file
            output_file = self.hourly_dir / f"{hour_key.replace(':', '-')}.json"
            with open(output_file, 'w') as f:
                data = {
                    lane: asdict(stats)
                    for lane, stats in hourly_stats.items()
                }
                json.dump(data, f, indent=2)

            logger.info(f"Saved hourly statistics to {output_file}")

        except Exception as e:
            logger.error(f"Error rotating hour: {e}")

    def export_hourly_csv(self, filepath: str = None) -> str:
        """
        Export hourly statistics to CSV.

        Args:
            filepath: Optional output filepath

        Returns:
            Path to saved file
        """
        if filepath is None:
            filepath = (
                self.hourly_dir /
                f"hourly_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )

        try:
            rows = []
            for hour_stats_dict in self.hourly_stats.values():
                if isinstance(hour_stats_dict, dict):
                    for lane, stats in hour_stats_dict.items():
                        if isinstance(stats, HourlyStatistics):
                            rows.append(asdict(stats))
                else:
                    rows.append(asdict(hour_stats_dict))

            if rows:
                with open(filepath, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)

            logger.info(f"Exported hourly statistics to {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error exporting hourly CSV: {e}")
            return ""

    def export_daily_csv(self, filepath: str = None) -> str:
        """
        Export daily statistics to CSV.

        Args:
            filepath: Optional output filepath

        Returns:
            Path to saved file
        """
        if filepath is None:
            filepath = (
                self.daily_dir /
                f"daily_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )

        try:
            rows = []
            for daily_stat in self.daily_stats.values():
                row = {k: v for k, v in asdict(daily_stat).items()
                      if k != 'lanes'}
                rows.append(row)

            if rows:
                with open(filepath, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)

            logger.info(f"Exported daily statistics to {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error exporting daily CSV: {e}")
            return ""

    def get_peak_hours(self, limit: int = 5) -> List[Tuple[int, int]]:
        """
        Get peak hours of the current day.

        Args:
            limit: Number of peak hours to return

        Returns:
            List of (hour, vehicle_count) tuples
        """
        today = datetime.now().date().isoformat()
        daily = self.get_daily_statistics(today)

        peak_hours = []
        for hour in range(24):
            count = 0
            for vehicle in self.vehicle_buffer:
                v_hour = datetime.fromisoformat(vehicle.timestamp).hour
                v_date = datetime.fromisoformat(vehicle.timestamp).date()
                if v_hour == hour and v_date.isoformat() == today:
                    count += 1
            if count > 0:
                peak_hours.append((hour, count))

        peak_hours.sort(key=lambda x: x[1], reverse=True)
        return peak_hours[:limit]

    def get_congestion_index(self, lane: Optional[str] = None) -> float:
        """
        Get current congestion index (0-1).

        Args:
            lane: Optional lane filter

        Returns:
            Congestion index
        """
        hourly = self.get_hourly_statistics(lane)

        if not hourly:
            return 0.0

        densities = [stats.traffic_density for stats in hourly.values()]
        return np.mean(densities) if densities else 0.0

    def get_summary_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive summary report.

        Returns:
            Dictionary with summary statistics
        """
        now = datetime.now()
        today = now.date().isoformat()

        hourly = self.get_hourly_statistics()
        daily = self.get_daily_statistics(today)

        total_vehicles = sum(v.total_vehicles for v in hourly.values())
        total_violations = sum(v.total_violations for v in hourly.values())
        avg_wait = np.mean([v.avg_wait_time for v in hourly.values()
                           if v.avg_wait_time > 0]) if hourly else 0.0

        return {
            'timestamp': now.isoformat(),
            'current_hour': now.hour,
            'date': today,
            'vehicles_this_hour': total_vehicles,
            'total_vehicles_today': daily.total_vehicles,
            'violations_this_hour': total_violations,
            'violations_today': daily.total_violations,
            'avg_wait_time_seconds': avg_wait,
            'peak_hours': daily.peak_hours,
            'busiest_hour': daily.busiest_hour,
            'congestion_index': self.get_congestion_index(),
            'lanes': {
                lane: {
                    'vehicles': stats.total_vehicles,
                    'violations': stats.total_violations,
                    'avg_wait_time': stats.avg_wait_time,
                    'congestion_level': stats.congestion_level
                }
                for lane, stats in hourly.items()
            }
        }
