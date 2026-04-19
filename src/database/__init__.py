"""
Database module for traffic management system v2.0.
Provides SQLAlchemy ORM models and database utilities.
"""

from src.database.models import (
    Base,
    Vehicle,
    VehicleDetection,
    Violation,
    ViolationRecord,
    WaitTimeObservation,
    HourlyStatistic,
    DailyStatistic,
    Lane,
    SignalState,
    TrafficSnapshot,
    SpeedTracking,
    CameraConfig,
    FineRule,
    VehicleClass,
    ViolationType,
    ViolationSeverity,
    CongestionLevel,
)
from src.database.config import (
    DatabaseConfig,
    get_database_url,
    get_engine,
    get_session_factory,
)
from src.database.manager import DatabaseManager

__all__ = [
    "Base",
    "Vehicle",
    "VehicleDetection",
    "Violation",
    "ViolationRecord",
    "WaitTimeObservation",
    "HourlyStatistic",
    "DailyStatistic",
    "Lane",
    "SignalState",
    "TrafficSnapshot",
    "SpeedTracking",
    "CameraConfig",
    "FineRule",
    "VehicleClass",
    "ViolationType",
    "ViolationSeverity",
    "CongestionLevel",
    "DatabaseConfig",
    "get_database_url",
    "get_engine",
    "get_session_factory",
    "DatabaseManager",
]
