"""
Database configuration module.

Supports SQLite for development and PostgreSQL for production.
"""

import os
from enum import Enum
from typing import Optional
from sqlalchemy import create_engine, Engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool, QueuePool


class DatabaseType(Enum):
    """Supported database types."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


class DatabaseConfig:
    """Database configuration."""

    def __init__(
        self,
        db_type: str = "sqlite",
        sqlite_path: str = "traffic.db",
        postgres_user: Optional[str] = None,
        postgres_password: Optional[str] = None,
        postgres_host: str = "localhost",
        postgres_port: int = 5432,
        postgres_db: str = "traffic_db",
        echo_sql: bool = False,
        pool_size: int = 10,
        max_overflow: int = 20,
    ):
        """
        Initialize database configuration.

        Args:
            db_type: Database type ('sqlite' or 'postgresql')
            sqlite_path: Path to SQLite database file
            postgres_user: PostgreSQL username
            postgres_password: PostgreSQL password
            postgres_host: PostgreSQL host
            postgres_port: PostgreSQL port
            postgres_db: PostgreSQL database name
            echo_sql: Enable SQL logging
            pool_size: Connection pool size (for PostgreSQL)
            max_overflow: Max overflow connections (for PostgreSQL)
        """
        self.db_type = DatabaseType(db_type.lower())
        self.sqlite_path = sqlite_path
        self.postgres_user = postgres_user or os.getenv("POSTGRES_USER", "postgres")
        self.postgres_password = postgres_password or os.getenv("POSTGRES_PASSWORD", "")
        self.postgres_host = postgres_host or os.getenv("POSTGRES_HOST", "localhost")
        self.postgres_port = postgres_port or int(os.getenv("POSTGRES_PORT", "5432"))
        self.postgres_db = postgres_db or os.getenv("POSTGRES_DB", "traffic_db")
        self.echo_sql = echo_sql
        self.pool_size = pool_size
        self.max_overflow = max_overflow

    def get_database_url(self) -> str:
        """Get database URL for SQLAlchemy."""
        if self.db_type == DatabaseType.SQLITE:
            return f"sqlite:///{self.sqlite_path}"
        elif self.db_type == DatabaseType.POSTGRESQL:
            if self.postgres_password:
                return (
                    f"postgresql://{self.postgres_user}:{self.postgres_password}@"
                    f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
                )
            else:
                return (
                    f"postgresql://{self.postgres_user}@"
                    f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
                )
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")


def get_database_url(config: DatabaseConfig) -> str:
    """Get database URL from config."""
    return config.get_database_url()


def get_engine(config: DatabaseConfig) -> Engine:
    """
    Create SQLAlchemy engine.

    Args:
        config: Database configuration

    Returns:
        SQLAlchemy Engine instance
    """
    url = config.get_database_url()

    if config.db_type == DatabaseType.SQLITE:
        # SQLite configuration
        engine = create_engine(
            url,
            echo=config.echo_sql,
            poolclass=StaticPool,  # Single connection for SQLite
            connect_args={"check_same_thread": False},
        )

        # Enable foreign keys for SQLite
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    else:  # PostgreSQL
        engine = create_engine(
            url,
            echo=config.echo_sql,
            poolclass=QueuePool,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_pre_ping=True,  # Test connections before using
        )

    return engine


def get_session_factory(engine: Engine):
    """
    Create SQLAlchemy session factory.

    Args:
        engine: SQLAlchemy Engine instance

    Returns:
        sessionmaker instance
    """
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_session(session_factory) -> Session:
    """Get a new database session."""
    return session_factory()
