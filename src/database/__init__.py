"""
Database module for traffic management system.

Provides SQLAlchemy ORM models and database utilities for:
- Vehicle detections and observations
- Traffic violations and incidents
- Wait time metrics
- Aggregated statistics (hourly/daily)
- Signal states and control history
"""

from src.database.models import (
    Base,
    VehicleDetection,
    ViolationRecord,
    WaitTimeObservation,
    HourlyStatistic,
    DailyStatistic,
    Lane,
    SignalState,
    TrafficSnapshot,
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
    "VehicleDetection",
    "ViolationRecord",
    "WaitTimeObservation",
    "HourlyStatistic",
    "DailyStatistic",
    "Lane",
    "SignalState",
    "TrafficSnapshot",
    "DatabaseConfig",
    "get_database_url",
    "get_engine",
    "get_session_factory",
    "DatabaseManager",
]
