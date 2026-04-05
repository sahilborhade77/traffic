"""
Integration layer between data aggregator and database.

Demonstrates how to:
- Persist aggregator data to database
- Restore statistics from database
- Synchronize in-memory and persistent storage
"""

from datetime import datetime
from typing import Optional, Dict, Any
import logging

from src.analytics.data_aggregator import TrafficDataAggregator
from src.database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class DatabaseAggregatorBridge:
    """
    Bridges data aggregator and database.
    
    Enables:
    - Persisting aggregator output to database
    - Querying historical data from database
    - Hybrid in-memory + persistent storage
    """

    def __init__(
        self,
        aggregator: TrafficDataAggregator,
        db_manager: DatabaseManager,
        auto_sync: bool = True,
    ):
        """
        Initialize bridge.

        Args:
            aggregator: TrafficDataAggregator instance
            db_manager: DatabaseManager instance
            auto_sync: Automatically sync hourly/daily stats to DB
        """
        self.aggregator = aggregator
        self.db_manager = db_manager
        self.auto_sync = auto_sync
        self.last_sync = datetime.utcnow()

    def add_vehicle_observation(
        self,
        lane: str,
        vehicle_class: str,
        speed: float,
        distance: Optional[float] = None,
        persist: bool = True,
        **kwargs
    ):
        """
        Add vehicle observation to both aggregator and database.

        Args:
            lane: Lane name
            vehicle_class: Vehicle class
            speed: Speed in m/s
            distance: Distance traveled
            persist: Also save to database
            **kwargs: Additional arguments (vehicle_id, position, bbox, etc.)
        """
        # Add to in-memory aggregator
        self.aggregator.add_vehicle_observation(
            lane=lane,
            vehicle_class=vehicle_class,
            speed=speed,
            distance=distance or (speed * 30),
        )

        # Persist to database
        if persist:
            self.db_manager.add_vehicle_detection(
                lane_name=lane,
                vehicle_id=kwargs.get("vehicle_id", 0),
                vehicle_class=vehicle_class,
                speed=speed,
                distance=distance,
                confidence=kwargs.get("confidence", 0.0),
                position_x=kwargs.get("position_x"),
                position_y=kwargs.get("position_y"),
                bbox=kwargs.get("bbox"),
                metadata=kwargs.get("metadata"),
                frame_id=kwargs.get("frame_id"),
            )

    def add_wait_time_observation(
        self,
        lane: str,
        wait_time: float,
        vehicle_type: str,
        vehicle_id: int,
        persist: bool = True,
        **kwargs
    ):
        """
        Add wait time observation to both aggregator and database.

        Args:
            lane: Lane name
            wait_time: Wait time in seconds
            vehicle_type: Vehicle type
            vehicle_id: Vehicle identifier
            persist: Also save to database
            **kwargs: Additional arguments (entry_time, exit_time, etc.)
        """
        # Add to in-memory aggregator
        self.aggregator.add_wait_time_observation(
            lane=lane,
            wait_time=wait_time,
            vehicle_type=vehicle_type,
            vehicle_id=vehicle_id,
        )

        # Persist to database
        if persist:
            self.db_manager.record_wait_time(
                lane_name=lane,
                vehicle_id=vehicle_id,
                vehicle_type=vehicle_type,
                wait_time_seconds=wait_time,
                entry_time=kwargs.get("entry_time"),
                exit_time=kwargs.get("exit_time"),
                stopped_duration=kwargs.get("stopped_duration"),
                metadata=kwargs.get("metadata"),
            )

    def record_violation(
        self,
        lane: str,
        violation_type: str,
        vehicle_id: int,
        severity: str = "medium",
        persist: bool = True,
        **kwargs
    ):
        """
        Record violation in both aggregator and database.

        Args:
            lane: Lane name
            violation_type: Type of violation
            vehicle_id: Vehicle ID
            severity: Severity level
            persist: Also save to database
            **kwargs: Additional violation details
        """
        # Add to in-memory aggregator
        self.aggregator.record_violation(
            lane=lane,
            violation_type=violation_type,
            vehicle_id=vehicle_id,
            severity=severity,
        )

        # Persist to database
        if persist:
            self.db_manager.record_violation(
                lane_name=lane,
                violation_type=violation_type,
                vehicle_id=vehicle_id,
                severity=severity,
                description=kwargs.get("description"),
                signal_state=kwargs.get("signal_state"),
                vehicle_speed=kwargs.get("vehicle_speed"),
                speed_limit=kwargs.get("speed_limit"),
                snapshot_path=kwargs.get("snapshot_path"),
                evidence_data=kwargs.get("evidence_data"),
            )

    def sync_hourly_stats_to_db(self):
        """Sync current hour's statistics to database."""
        hourly_stats = self.aggregator.get_hourly_statistics()

        count = 0
        for lane_name, stats in hourly_stats.items():
            try:
                self.db_manager.store_hourly_statistic(
                    lane_name=lane_name,
                    hour=stats.hour,
                    total_vehicles=stats.total_vehicles,
                    vehicle_breakdown=stats.vehicle_breakdown,
                    avg_wait_time=stats.avg_wait_time,
                    max_wait_time=stats.max_wait_time,
                    min_wait_time=stats.min_wait_time,
                    total_violations=stats.total_violations,
                    peak_hour=stats.peak_hour,
                    avg_vehicle_speed=stats.avg_vehicle_speed,
                    traffic_density=stats.traffic_density,
                    congestion_level=stats.congestion_level,
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to sync hourly stats for {lane_name}: {e}")

        logger.info(f"Synced {count} hourly statistics to database")
        return count

    def sync_daily_stats_to_db(self):
        """Sync daily statistics to database."""
        daily_stats = self.aggregator.get_daily_statistics()

        try:
            self.db_manager.store_daily_statistic(
                lane_name="All",  # Simplified for demo
                date=daily_stats.date,
                day_of_week=daily_stats.day_of_week,
                total_vehicles=daily_stats.total_vehicles,
                vehicle_breakdown=daily_stats.vehicle_breakdown,
                avg_wait_time=daily_stats.avg_wait_time,
                peak_hours=daily_stats.peak_hours,
                total_violations=daily_stats.total_violations,
                avg_traffic_density=daily_stats.avg_traffic_density,
                avg_vehicle_speed=daily_stats.avg_vehicle_speed,
                busiest_hour=daily_stats.busiest_hour,
            )
            logger.info(f"Synced daily statistics to database")
            return 1
        except Exception as e:
            logger.error(f"Failed to sync daily stats: {e}")
            return 0

    def get_historical_stats(
        self, lane: Optional[str] = None, days: int = 7
    ) -> Dict[str, Any]:
        """
        Get historical statistics from database.

        Args:
            lane: Optional lane filter
            days: Number of days to retrieve

        Returns:
            Dictionary with historical data
        """
        daily_stats = self.db_manager.get_daily_statistics(
            lane_name=lane, days=days
        )
        hourly_stats = self.db_manager.get_hourly_statistics(
            lane_name=lane, hours=days * 24
        )

        return {
            "daily": [
                {
                    "date": s.date,
                    "total_vehicles": s.total_vehicles,
                    "violations": s.total_violations,
                    "avg_wait_time": s.avg_wait_time,
                    "vehicle_breakdown": s.vehicle_breakdown,
                }
                for s in daily_stats
            ],
            "hourly": [
                {
                    "datetime": s.datetime.isoformat(),
                    "hour": s.hour,
                    "total_vehicles": s.total_vehicles,
                    "traffic_density": s.traffic_density,
                }
                for s in hourly_stats
            ],
        }

    def export_to_db(self):
        """Export all current aggregator data to database."""
        logger.info("Exporting aggregator data to database...")

        # Export hourly stats
        hourly_count = self.sync_hourly_stats_to_db()

        # Export daily stats
        daily_count = self.sync_daily_stats_to_db()

        logger.info(
            f"Export completed: {hourly_count} hourly + {daily_count} daily statistics"
        )
        return hourly_count + daily_count
