"""
Feature 9: Alembic env.py — Database Migration Configuration
--------------------------------------------------------------
Configured for TIS ViolationDatabase models (SQLAlchemy Base).
Supports both online (PostgreSQL) and offline (SQLite) modes.
"""

from logging.config import fileConfig
import os
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import TIS models so Alembic can detect schema changes
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from src.database.violation_db import Base

# Alembic Config object — provides access to alembic.ini values
config = context.config

# Setup logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Point Alembic at TIS models metadata
target_metadata = Base.metadata

# Override sqlalchemy.url from environment variable if available
db_url = os.getenv('DATABASE_URL', 'sqlite:///traffic.db')
config.set_main_option('sqlalchemy.url', db_url)


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates SQL scripts)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
