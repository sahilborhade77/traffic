"""
Database usage demonstrations and examples.

Shows:
- Database initialization and configuration
- CRUD operations for all models
- Querying and filtering data
- Integration with data aggregator
- Performance optimization
"""

import logging
from datetime import datetime, timedelta
from src.database.config import DatabaseConfig
from src.database.init import DatabaseInitializer
from src.database.manager import DatabaseManager
from src.database.integration import DatabaseAggregatorBridge
from src.analytics.data_aggregator import TrafficDataAggregator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_basic_setup():
    """
    Example 1: Basic database setup and initialization.
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Database Setup")
    print("="*80 + "\n")

    # SQLite configuration (default)
    config = DatabaseConfig(
        db_type="sqlite",
        sqlite_path="traffic_dev.db",
        echo_sql=False,
    )

    initializer = DatabaseInitializer(config)
    success = initializer.initialize(drop_existing=True)

    if success:
        print("[OK] Database initialized successfully")
        print(f"[DB] {initializer.get_database_info()}")
    else:
        print("[ERROR] Database initialization failed")
        return None

    return initializer.manager


def example_vehicle_detection(db: DatabaseManager):
    """
    Example 2: Recording vehicle detections.
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: Vehicle Detection Recording")
    print("="*80 + "\n")

    # Record detections
    lanes = ["North", "South", "East", "West"]
    vehicle_classes = ["car", "truck", "motorcycle"]

    print("[RECORD] Adding vehicle detections...")
    for i in range(20):
        lane = lanes[i % 4]
        v_class = vehicle_classes[i % 3]
        speed = 10 + (i % 15)

        detection = db.add_vehicle_detection(
            lane_name=lane,
            vehicle_id=1000 + i,
            vehicle_class=v_class,
            speed=float(speed),
            confidence=0.85 + (i % 10) * 0.01,
            bbox=(100 + i * 5, 100 + i * 5, 150 + i * 5, 150 + i * 5),
            metadata={"detector": "yolov8n", "cluster_id": i},
        )
        print(f"  • Recorded: {detection}")

    # Query detections
    print("\n[QUERY] Recent detections (last 24 hours):")
    detections = db.get_vehicle_detections(lane_name="North", hours=24, limit=5)
    for det in detections:
        print(
            f"  • Vehicle: {det.vehicle_id}, "
            f"Class: {det.vehicle_class}, Speed: {det.speed:.1f} m/s"
        )

    # Speed statistics
    print("\n[STATS] Speed statistics for North lane:")
    speed_stats = db.get_vehicle_speed_stats("North", hours=24)
    for stat, value in speed_stats.items():
        if isinstance(value, float):
            print(f"  • {stat.upper()}: {value:.2f} m/s")
        else:
            print(f"  • {stat.upper()}: {value}")


def example_violations(db: DatabaseManager):
    """
    Example 3: Recording and querying violations.
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Violation Recording")
    print("="*80 + "\n")

    # Record violations
    violation_types = ["red_light", "speeding", "illegal_turn"]
    severities = ["low", "medium", "high", "critical"]

    print("[RECORD] Recording violations...")
    for i in range(10):
        violation = db.record_violation(
            lane_name=["North", "South", "East", "West"][i % 4],
            violation_type=violation_types[i % 3],
            vehicle_id=2000 + i,
            severity=severities[i % 4],
            description=f"Violation {i}: automated detection",
            signal_state="red" if i % 2 == 0 else "green",
            vehicle_speed=45 + (i % 20),
            speed_limit=50.0,
        )
        print(f"  • {violation.violation_type.value}: {violation.severity.value}")

    # Query violations
    print("\n[QUERY] All violations (last 24 hours):")
    violations = db.get_violations(hours=24, limit=5)
    for v in violations:
        print(
            f"  • Type: {v.violation_type.value}, "
            f"Severity: {v.severity.value}"
        )

    # Violation summary
    print("\n[SUMMARY] Violation statistics:")
    summary = db.get_violation_summary(days=1)
    print(f"  • Total violations: {summary['total']}")
    print(f"  • Critical violations: {summary['critical_count']}")
    print(f"  • By type: {summary['by_type']}")


def example_wait_times(db: DatabaseManager):
    """
    Example 4: Recording and analyzing wait times.
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: Wait Time Analysis")
    print("="*80 + "\n")

    # Record wait times
    print("[RECORD] Recording wait time observations...")
    for i in range(15):
        lane = ["North", "South", "East", "West"][i % 4]
        wait_time = 20 + (i % 60)

        observation = db.record_wait_time(
            lane_name=lane,
            vehicle_id=3000 + i,
            vehicle_type="car" if i % 2 == 0 else "truck",
            wait_time_seconds=float(wait_time),
            entry_time=datetime.utcnow() - timedelta(minutes=wait_time),
            exit_time=datetime.utcnow(),
            stopped_duration=float(wait_time * 0.8),
        )
        print(f"  • {lane}: {wait_time}s wait time")

    # Wait time statistics
    print("\n[STATS] Wait time statistics by lane:")
    for lane in ["North", "South", "East", "West"]:
        stats = db.get_wait_time_stats(lane, hours=24)
        if stats:
            print(
                f"  {lane}: Avg={stats['avg']:.1f}s, "
                f"Min={stats['min']:.1f}s, Max={stats['max']:.1f}s"
            )


def example_statistics(db: DatabaseManager):
    """
    Example 5: Storing and querying statistics.
    """
    print("\n" + "="*80)
    print("EXAMPLE 5: Statistics Management")
    print("="*80 + "\n")

    # Store hourly statistics
    print("[RECORD] Storing hourly statistics...")
    hourly = db.store_hourly_statistic(
        lane_name="North",
        hour=14,
        total_vehicles=100,
        vehicle_breakdown={"car": 60, "truck": 30, "motorcycle": 10},
        avg_wait_time=45.5,
        max_wait_time=120.0,
        min_wait_time=5.0,
        total_violations=3,
        peak_hour=True,
        avg_vehicle_speed=12.5,
        traffic_density=0.75,
        congestion_level="high",
    )
    print(f"  • Stored hourly stat: Hour {hourly.hour}, Vehicles={hourly.total_vehicles}")

    # Store daily statistics
    print("\n[RECORD] Storing daily statistics...")
    daily = db.store_daily_statistic(
        lane_name="North",
        date="2026-04-02",
        day_of_week="Thursday",
        total_vehicles=1500,
        vehicle_breakdown={"car": 900, "truck": 450, "motorcycle": 150},
        avg_wait_time=38.2,
        peak_hours=[12, 13, 14, 17, 18],
        total_violations=28,
        avg_traffic_density=0.65,
        avg_vehicle_speed=13.2,
        busiest_hour=14,
    )
    print(f"  • Stored daily stat: {daily.date}, Vehicles={daily.total_vehicles}")

    # Query hourly statistics
    print("\n[QUERY] Hourly statistics (last 24 hours):")
    hourly_stats = db.get_hourly_statistics(lane_name="North", hours=24, limit=3)
    for stat in hourly_stats:
        print(
            f"  • Hour {stat.hour}: {stat.total_vehicles} vehicles, "
            f"Congestion={stat.congestion_level.value}"
        )

    # Query daily statistics
    print("\n[QUERY] Daily statistics (last 7 days):")
    daily_stats = db.get_daily_statistics(lane_name="North", days=7, limit=3)
    for stat in daily_stats:
        print(
            f"  • {stat.date} ({stat.day_of_week}): {stat.total_vehicles} vehicles, "
            f"{stat.total_violations} violations"
        )


def example_integration_with_aggregator():
    """
    Example 6: Integrating database with data aggregator.
    """
    print("\n" + "="*80)
    print("EXAMPLE 6: Database + Aggregator Integration")
    print("="*80 + "\n")

    # Initialize database
    config = DatabaseConfig(db_type="sqlite", sqlite_path="traffic_integrated.db")
    initializer = DatabaseInitializer(config)
    initializer.initialize(drop_existing=True)
    db = initializer.manager

    # Initialize aggregator
    aggregator = TrafficDataAggregator(data_dir="data")

    # Create bridge
    bridge = DatabaseAggregatorBridge(aggregator, db, auto_sync=True)

    # Add observations through bridge
    print("[ADD] Recording observations through bridge...")
    for i in range(30):
        lane = ["North", "South", "East", "West"][i % 4]
        v_class = ["car", "truck", "motorcycle"][i % 3]

        bridge.add_vehicle_observation(
            lane=lane,
            vehicle_class=v_class,
            speed=10 + (i % 15),
            vehicle_id=1000 + i,
        )

        if i % 10 == 0:
            bridge.add_wait_time_observation(
                lane=lane,
                vehicle_type=v_class,
                vehicle_id=2000 + i,
                wait_time=30 + (i % 40),
            )

            if i % 15 == 0:
                bridge.record_violation(
                    lane=lane,
                    violation_type="red_light",
                    vehicle_id=3000 + i,
                    severity="medium",
                )

    print(f"  • Added {i + 1} observations")

    # Sync to database
    print("\n[SYNC] Exporting statistics to database...")
    count = bridge.export_to_db()
    print(f"  • Synced {count} statistics to database")

    # Query from database
    print("\n[QUERY] Retrieved historical data from database:")
    historical = bridge.get_historical_stats(days=1)
    daily_count = len(historical["daily"])
    hourly_count = len(historical["hourly"])
    print(f"  • Daily records: {daily_count}")
    print(f"  • Hourly records: {hourly_count}")


def main():
    """Run all examples."""
    print("\n" + "="*80)
    print("DATABASE USAGE EXAMPLES")
    print("="*80)

    # Example 1: Setup
    db = example_basic_setup()
    if not db:
        return

    # Example 2: Vehicle detections
    example_vehicle_detection(db)

    # Example 3: Violations
    example_violations(db)

    # Example 4: Wait times
    example_wait_times(db)

    # Example 5: Statistics
    example_statistics(db)

    # Example 6: Integration
    example_integration_with_aggregator()

    print("\n" + "="*80)
    print("[OK] All examples completed successfully!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
