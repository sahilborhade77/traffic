# Database Integration - Quick Start Guide

## 30-Second Setup

```python
from src.database.init import init_database

# For development (SQLite)
db = init_database()

# For production (PostgreSQL)
db = init_database(db_type="postgresql")
```

## Common Operations

### Record Data
```python
# Vehicle detection
db.add_vehicle_detection(lane_name="North", vehicle_id=1, vehicle_class="car", speed=12.5)

# Traffic violation
db.record_violation(lane_name="North", violation_type="red_light", vehicle_id=1, severity="high")

# Wait time
db.record_wait_time(lane_name="North", vehicle_id=1, vehicle_type="car", wait_time_seconds=45.0)

# Signal state
db.record_signal_state(lane_name="North", state="green", duration=30.0)

# Statistics
db.store_hourly_statistic(lane_name="North", hour=14, total_vehicles=100, ...)
db.store_daily_statistic(lane_name="North", date="2026-04-02", total_vehicles=2500, ...)
```

### Query Data
```python
# Get detections
detections = db.get_vehicle_detections(lane_name="North", hours=24)

# Get violations
violations = db.get_violations(lane_name="North", hours=24)
summary = db.get_violation_summary(days=7)

# Get statistics
hourly = db.get_hourly_statistics(lane_name="North", hours=24)
daily = db.get_daily_statistics(lane_name="North", days=30)

# Get analytics
speed_stats = db.get_vehicle_speed_stats("North")  # {avg, min, max, count}
wait_stats = db.get_wait_time_stats("North")      # {avg, min, max, count}
```

## With Data Aggregator

```python
from src.analytics.data_aggregator import TrafficDataAggregator
from src.database.integration import DatabaseAggregatorBridge

aggregator = TrafficDataAggregator()
db = init_database()
bridge = DatabaseAggregatorBridge(aggregator, db)

# Add via bridge (synced to DB automatically)
bridge.add_vehicle_observation(lane="North", vehicle_class="car", speed=12.5)
bridge.add_wait_time_observation(lane="North", vehicle_id=1, vehicle_type="car", wait_time=45.0)
bridge.record_violation(lane="North", violation_type="red_light", vehicle_id=1)

# Sync stats to database
bridge.sync_hourly_stats_to_db()
bridge.sync_daily_stats_to_db()

# Query from database
history = bridge.get_historical_stats(days=7)
```

## Tables Available

| Table | Purpose |
|-------|---------|
| **lanes** | Lane configuration |
| **vehicle_detections** | Real-time detections |
| **violation_records** | Traffic violations |
| **wait_time_observations** | Wait time metrics |
| **hourly_statistics** | Hourly stats |
| **daily_statistics** | Daily summaries |
| **signal_states** | Signal history |
| **traffic_snapshots** | Traffic snapshots |

## Configuration

### SQLite (Development)
```bash
DB_TYPE=sqlite
SQLITE_PATH=traffic.db
```

### PostgreSQL (Production)
```bash
DB_TYPE=postgresql
POSTGRES_USER=traffic_app
POSTGRES_PASSWORD=secure_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=traffic_db
```

## Test It

```bash
# Run all examples
python -m src.database.examples

# Expected output: "[OK] All examples completed successfully!"
```

## Files Created

- `src/database/__init__.py` - Package exports
- `src/database/config.py` - Configuration (120 lines)
- `src/database/models.py` - ORM models (400 lines)
- `src/database/manager.py` - CRUD operations (600 lines)
- `src/database/init.py` - Initialization (80 lines)
- `src/database/integration.py` - Aggregator bridge (280 lines)
- `src/database/examples.py` - Working examples (340 lines)
- `DATABASE_INTEGRATION.md` - Full API reference
- `POSTGRES_SETUP.md` - PostgreSQL setup guide

## Databases Supported

✅ **SQLite** - Development/testing
✅ **PostgreSQL** - Production (recommended)

## Next: Integrate with API

```python
# In src/dashboard/api.py
from src.database.init import init_database

db = init_database()

@app.get("/api/violations")
async def get_violations(hours: int = 24):
    return {"data": db.get_violations(hours=hours)}

@app.get("/api/violations/summary")
async def violations_summary(days: int = 7):
    return db.get_violation_summary(days=days)
```

---

**For complete documentation, see:**
- `DATABASE_INTEGRATION.md` - Complete API reference
- `POSTGRES_SETUP.md` - Production PostgreSQL setup
- `STEP_13_DATABASE_INTEGRATION.md` - Implementation summary
