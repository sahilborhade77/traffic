"""
Database initialization and migration utilities.

Handles:
- Database table creation
- Schema initialization
- Data migration from in-memory to database
- Backup and restoration
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from src.database.config import DatabaseConfig, get_engine, get_session_factory
from src.database.models import Base
from src.database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Handles database initialization and migrations."""

    def __init__(self, config: DatabaseConfig):
        """
        Initialize database initializer.

        Args:
            config: DatabaseConfig instance
        """
        self.config = config
        self.engine = get_engine(config)
        self.session_factory = get_session_factory(self.engine)
        self.manager = DatabaseManager(self.session_factory)

    def initialize(self, drop_existing: bool = False) -> bool:
        """
        Initialize database schema.

        Args:
            drop_existing: Whether to drop existing tables

        Returns:
            True if successful
        """
        try:
            logger.info(f"Initializing database: {self.config.db_type.value}")

            if drop_existing:
                logger.warning("Dropping all existing tables...")
                self.manager.drop_all_tables(self.engine)

            logger.info("Creating tables...")
            self.manager.create_tables(self.engine)
            logger.info("Database initialization completed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False

    def verify_connection(self) -> bool:
        """Verify database connection."""
        try:
            session = self.session_factory()
            session.execute("SELECT 1")
            session.close()
            logger.info("Database connection verified")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False

    def get_database_info(self) -> dict:
        """Get database information."""
        return {
            "type": self.config.db_type.value,
            "url": self.config.get_database_url(),
            "echo_sql": self.config.echo_sql,
        }


def init_database(
    db_type: str = "sqlite",
    echo_sql: bool = False,
    sqlite_path: str = "traffic.db",
    drop_existing: bool = False,
) -> DatabaseManager:
    """
    Quick initialization function.

    Args:
        db_type: 'sqlite' or 'postgresql'
        echo_sql: Enable SQL logging
        sqlite_path: Path to SQLite database (if using SQLite)
        drop_existing: Drop existing tables

    Returns:
        DatabaseManager instance
    """
    config = DatabaseConfig(
        db_type=db_type,
        sqlite_path=sqlite_path,
        echo_sql=echo_sql,
    )

    initializer = DatabaseInitializer(config)
    initializer.initialize(drop_existing=drop_existing)

    return initializer.manager


def init_database_from_env() -> DatabaseManager:
    """Initialize database from environment variables."""
    import os

    db_type = os.getenv("DB_TYPE", "sqlite")
    sqlite_path = os.getenv("SQLITE_PATH", "traffic.db")
    echo_sql = os.getenv("ECHO_SQL", "false").lower() == "true"

    return init_database(
        db_type=db_type,
        sqlite_path=sqlite_path,
        echo_sql=echo_sql,
    )
