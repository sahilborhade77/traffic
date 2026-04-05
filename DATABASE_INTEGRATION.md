# Database Integration Documentation

## Overview

The traffic management system now includes comprehensive database integration using SQLAlchemy ORM, supporting both SQLite (development) and PostgreSQL (production).

**Key Features:**
- ✅ SQLite for rapid development and testing
- ✅ PostgreSQL for production deployments
- ✅ Full ORM models with relationships
- ✅ Automatic table creation and migrations
- ✅ Integration bridge with data aggregator
- ✅ Comprehensive CRUD operations
- ✅ Historical data queries and analytics

---

## Database Schema

### Core Tables

#### 1. `lanes` - Lane Configuration
Stores intersection lane definitions and metadata.

```
lanes (id PK, name, direction, intersection_id, capacity, speed_limit, ...)
```

**Relationships:**
- Has many: detections, violations, wait_times, hourly_stats, daily_stats, signal_states, snapshots

---

#### 2. `vehicle_detections` - Real-time Vehicle Detections
Records vehicle detection data from YOLO + tracker systems.

```
vehicle_detections (id PK, timestamp, frame_id, vehicle_id, lane_id FK, 
                    vehicle_class, confidence, speed, distance, 
                    position_x, position_y, bbox_*, metadata)
```

**Indexes:**
- `idx_detection_timestamp_lane` - Fast queries by time and lane
- `idx_detection_vehicle_id` - Track vehicles over time

**Example Usage:**
```python
db.add_vehicle_detection(
    lane_name="North",
    vehicle_id=1001,
    vehicle_class="car",
    speed=12.5,
    confidence=0.95,
    bbox=(100, 100, 150, 150)
)
```

---

#### 3. `violation_records` - Traffic Violations
Stores all traffic violations with evidence and enforcement status.

```
violation_records (id PK, timestamp, lane_id FK, vehicle_id, 
                   violation_type, severity, description, 
                   signal_state, vehicle_speed, speed_limit, 
                   snapshot_path, evidence_data, processed, 
                   enforcement_issued, fine_amount)
```

**Violation Types:**
- `red_light` - Running red light
- `speeding` - Exceeding speed limit
- `illegal_turn` - Prohibited turning
- `wrong_way` - Wrong direction
- `illegal_stop` - Parking violation
- `parking_violation` - Parking offense
- `other` - Miscellaneous

**Severity Levels:**
- `low` - Minor violation
- `medium` - Standard violation
- `high` - Serious violation
- `critical` - Dangerous violation

**Indexes:**
- `idx_violation_timestamp_lane` - Time-based queries
- `idx_violation_processed` - Find unprocessed violations

**Example Usage:**
```python
db.record_violation(
    lane_name="North",
    violation_type="red_light",
    vehicle_id=1001,
    severity="high",
    vehicle_speed=45.2,
    speed_limit=50.0,
    snapshot_path="/snapshots/2026-04-02-14-30-45.jpg",
    evidence_data={"datetime": "2026-04-02T14:30:45", "frame_id": 1234}
)
```

---

#### 4. `wait_time_observations` - Vehicle Wait Times
Records wait time metrics at intersections.

```
wait_time_observations (id PK, timestamp, lane_id FK, vehicle_id, 
                        vehicle_type, wait_time_seconds, 
                        entry_time, exit_time, stopped_duration, metadata)
```

**Example Usage:**
```python
db.record_wait_time(
    lane_name="North",
    vehicle_id=1001,
    vehicle_type="car",
    wait_time_seconds=45.3,
    entry_time=datetime(...),
    exit_time=datetime(...),
    stopped_duration=36.0
)
```

---

#### 5. `hourly_statistics` - Hourly Aggregated Stats
Hourly traffic statistics aggregated by lane.

```
hourly_statistics (id PK, datetime, hour, lane_id FK, 
                   total_vehicles, vehicle_breakdown, 
                   avg_wait_time, max_wait_time, min_wait_time,
                   total_violations, violation_breakdown,
                   peak_hour, avg_vehicle_speed, 
                   traffic_density, congestion_level, metadata)
```

**Congestion Levels:**
- `low` - < 30% capacity
- `medium` - 30-60% capacity
- `high` - 60-85% capacity
- `critical` - > 85% capacity

**Example Usage:**
```python
db.store_hourly_statistic(
    lane_name="North",
    hour=14,
    total_vehicles=150,
    vehicle_breakdown={"car": 100, "truck": 40, "motorcycle": 10},
    avg_wait_time=45.5,
    max_wait_time=120.0,
    min_wait_time=5.0,
    total_violations=3,
    peak_hour=True,
    traffic_density=0.75,
    congestion_level="high"
)
```

---

#### 6. `daily_statistics` - Daily Aggregated Stats
Comprehensive daily traffic statistics.

```
daily_statistics (id PK, date, day_of_week, lane_id FK,
                  total_vehicles, vehicle_breakdown,
                  avg_wait_time, peak_hours, busiest_hour,
                  total_violations, violation_breakdown,
                  avg_traffic_density, avg_vehicle_speed, metadata)
```

**Example Usage:**
```python
db.store_daily_statistic(
    lane_name="North",
    date="2026-04-02",
    day_of_week="Thursday",
    total_vehicles=2500,
    vehicle_breakdown={"car": 1500, "truck": 750, "motorcycle": 250},
    avg_wait_time=42.1,
    peak_hours=[12, 13, 14, 17, 18],
    busiest_hour=14,
    total_violations=45
)
```

---

#### 7. `signal_states` - Traffic Signal History
Records traffic signal state changes and duration.

```
signal_states (id PK, timestamp, lane_id FK, state, duration,
               adaptive_mode, queue_length, response_time, metadata)
```

**States:**
- `red` - Stop signal
- `yellow` - Caution signal
- `green` - Go signal

---

#### 8. `traffic_snapshots` - Periodic Traffic Snapshots
Periodic snapshots of traffic conditions for visualization.

```
traffic_snapshots (id PK, timestamp, lane_id FK, active_vehicles,
                   congestion_level, avg_speed, violations_count,
                   avg_wait_time, signal_state, metadata)
```

---

## Configuration

### SQLite (Development)

```python
from src.database.config import DatabaseConfig
from src.database.init import DatabaseInitializer

config = DatabaseConfig(
    db_type="sqlite",
    sqlite_path="traffic.db",
    echo_sql=False
)

initializer = DatabaseInitializer(config)
initializer.initialize()
```

### PostgreSQL (Production)

```python
config = DatabaseConfig(
    db_type="postgresql",
    postgres_user="traffic_app",
    postgres_password="secure_password",
    postgres_host="db.example.com",
    postgres_port=5432,
    postgres_db="traffic_db",
    pool_size=20,
    max_overflow=40
)
```

### Environment Variables

```bash
DB_TYPE=postgresql
POSTGRES_USER=traffic_app
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=traffic_db
ECHO_SQL=false
```

---

## Usage Examples

### 1. Basic Setup

```python
from src.database.init import init_database

# Quick initialization
db = init_database(db_type="sqlite", echo_sql=False)
```

### 2. Record Vehicle Detection

```python
detection = db.add_vehicle_detection(
    lane_name="North",
    vehicle_id=1001,
    vehicle_class="car",
    speed=12.5,
    confidence=0.95,
    position_x=320,
    position_y=240,
    bbox=(100, 100, 150, 150),
    metadata={"detector": "yolov8n"}
)
```

### 3. Record Violation

```python
violation = db.record_violation(
    lane_name="North",
    violation_type="red_light",
    vehicle_id=1001,
    severity="high",
    vehicle_speed=45.0,
    speed_limit=50.0,
    snapshot_path="/snapshots/violation_001.jpg"
)
```

### 4. Query Historical Data

```python
# Get recent detections
detections = db.get_vehicle_detections(
    lane_name="North",
    hours=24,
    limit=100
)

# Get violations
violations = db.get_violations(
    lane_name="North",
    violation_type="speeding",
    hours=24,
    limit=50
)

# Get statistics
hourly_stats = db.get_hourly_statistics(
    lane_name="North",
    hours=24,
    limit=100
)

daily_stats = db.get_daily_statistics(
    lane_name="North",
    days=30,
    limit=365
)
```

### 5. Integration with Data Aggregator

```python
from src.analytics.data_aggregator import TrafficDataAggregator
from src.database.integration import DatabaseAggregatorBridge

aggregator = TrafficDataAggregator()
db = init_database()

# Create bridge
bridge = DatabaseAggregatorBridge(aggregator, db, auto_sync=True)

# Add observations (automatically synced to DB)
bridge.add_vehicle_observation(
    lane="North",
    vehicle_class="car",
    speed=12.5,
    vehicle_id=1001
)

# Sync stats to database
bridge.sync_hourly_stats_to_db()
bridge.sync_daily_stats_to_db()

# Query historical data from database
historical = bridge.get_historical_stats(days=7)
```

---

## Querying and Analytics

### Get Speed Statistics

```python
stats = db.get_vehicle_speed_stats("North", hours=24)
# Returns: {"avg": 12.5, "min": 5.0, "max": 25.0, "count": 150}
```

### Get Wait Time Statistics

```python
stats = db.get_wait_time_stats("North", hours=24)
# Returns: {"avg": 45.2, "min": 5.0, "max": 120.0, "count": 85}
```

### Get Violation Summary

```python
summary = db.get_violation_summary(days=7)
# Returns: {
#     "total": 45,
#     "by_type": {"red_light": 20, "speeding": 15, "illegal_turn": 10},
#     "by_severity": {"low": 10, "medium": 20, "high": 10, "critical": 5},
#     "critical_count": 5
# }
```

---

## API Integration

The API can be updated to use the database:

```python
from fastapi import FastAPI
from src.database.init import init_database

app = FastAPI()
db = init_database()

@app.get("/api/violations")
async def get_violations(lane: Optional[str] = None, hours: int = 24):
    violations = db.get_violations(lane_name=lane, hours=hours)
    return {"violations": [v.to_dict() for v in violations]}

@app.get("/api/analytics/daily")
async def get_daily_analytics(lane: Optional[str] = None, days: int = 30):
    stats = db.get_daily_statistics(lane_name=lane, days=days)
    return {"statistics": [s.to_dict() for s in stats]}
```

---

## Performance Optimization

### Indexing Strategy
- Time-based queries: `idx_detection_timestamp_lane`
- Lane-based filtering: Foreign key on `lane_id`
- Vehicle tracking: `idx_detection_vehicle_id`
- Processed status: `idx_violation_processed`

### Connection Pooling (PostgreSQL)
```python
config = DatabaseConfig(
    db_type="postgresql",
    pool_size=20,
    max_overflow=40
)
```

### Query Optimization
- Use `limit` parameter to restrict result set
- Filter by `hours` or `days` to narrow time window
- Specify `lane_name` for lane-specific queries

### Batch Operations
```python
# Bulk insert detections
session = db.get_session()
for detection_data in detections_list:
    session.add(VehicleDetection(**detection_data))
session.commit()
```

---

## Backup and Recovery

### Export Data to CSV
```python
# Use data aggregator export functions
aggregator.export_hourly_csv()
aggregator.export_daily_csv()
```

### PostgreSQL Backup
```bash
pg_dump -U traffic_app -h localhost traffic_db > backup.sql
```

### PostgreSQL Restore
```bash
psql -U traffic_app -h localhost traffic_db < backup.sql
```

---

## Migration Guide (In-Memory to Database)

### Step 1: Initialize Database
```python
from src.database.init import init_database
db = init_database(db_type="sqlite")
```

### Step 2: Set Up Bridge
```python
from src.database.integration import DatabaseAggregatorBridge
aggregator = TrafficDataAggregator()
bridge = DatabaseAggregatorBridge(aggregator, db)
```

### Step 3: Migrate Existing Data
```python
# Add historical data
for detection in historical_detections:
    db.add_vehicle_detection(**detection)

# Sync aggregator stats
bridge.export_to_db()
```

### Step 4: Update Application
- Replace in-memory operations with database calls
- Use bridge for dual in-memory + persistent storage
- Query database for historical analytics

---

## Troubleshooting

### Connection Issues
```python
initializer = DatabaseInitializer(config)
if not initializer.verify_connection():
    print("Database connection failed")
```

### Table Not Found
```python
# Recreate tables
initializer.initialize(drop_existing=False)
```

### Performance Issues
- Check indexes are created
- Adjust pool size for PostgreSQL
- Use `explain` for slow queries

---

## File Structure

```
src/database/
├── __init__.py           # Package initialization and exports
├── config.py             # Database configuration
├── models.py             # SQLAlchemy ORM models
├── manager.py            # Database manager CRUD operations
├── init.py               # Initialization and helper functions
├── integration.py        # Bridge between aggregator and DB
└── examples.py           # Usage examples and demonstrations
```

---

## Next Steps

1. **Test Database Integration**
   ```bash
   python src/database/examples.py
   ```

2. **Update API to Use Database**
   - Modify endpoints in `src/dashboard/api.py`
   - Use `DatabaseManager` for queries
   - Add database-backed endpoints

3. **Configure Production PostgreSQL**
   - Set up PostgreSQL server
   - Configure environment variables
   - Create database and user
   - Run migrations

4. **Add Monitoring**
   - Database query performance metrics
   - Connection pool statistics
   - Storage usage monitoring

5. **Implement Advanced Features**
   - Data archival for old records
   - Real-time database sync
   - Custom analytics queries
   - Data export and reporting

---

## Reference

**SQLAlchemy Documentation:** https://docs.sqlalchemy.org/
**PostgreSQL Documentation:** https://www.postgresql.org/docs/
