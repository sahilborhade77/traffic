# PostgreSQL Setup Guide - Production Database

## Quick Start

### Windows Setup

#### 1. Install PostgreSQL

**Option A: Using Installer (Recommended)**
1. Download PostgreSQL from https://www.postgresql.org/download/windows/
2. Run installer
3. Set superuser password (remember this!)
4. Accept default port 5432
5. Select English locale

**Option B: Using Docker**
```bash
docker run --name traffic-postgres \
  -e POSTGRES_USER=traffic_app \
  -e POSTGRES_PASSWORD=your_secure_password \
  -e POSTGRES_DB=traffic_db \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  -d postgres:15-alpine
```

#### 2. Create Database and User

**Using pgAdmin (GUI)**
1. Open pgAdmin (Windows Start Menu)
2. Connect to local server
3. Create new database: `traffic_db`
4. Create user:
   - Username: `traffic_app`
   - Password: (set secure password)
5. Grant privileges:
   - Right-click user → Properties
   - Privileges → Can create DB: ON

**Using Command Line (psql)**
```bash
# Connect as superuser
psql -U postgres

# Create database
CREATE DATABASE traffic_db;

# Create user
CREATE USER traffic_app WITH PASSWORD 'your_secure_password';

# Grant privileges
ALTER ROLE traffic_app CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE traffic_db TO traffic_app;

# Connect to database and grant schema privileges
\c traffic_db
GRANT ALL PRIVILEGES ON SCHEMA public TO traffic_app;

# Verify
\du  # List users
\l   # List databases

# Exit
\q
```

#### 3. Test Connection

```bash
psql -U traffic_app -h localhost -d traffic_db
# Enter password when prompted
# Should show: traffic_db=>
```

### Linux Setup (Ubuntu/Debian)

```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql  # Auto-start on boot

# Create database and user
sudo -u postgres psql

# Inside psql:
CREATE DATABASE traffic_db;
CREATE USER traffic_app WITH PASSWORD 'your_secure_password';
ALTER ROLE traffic_app CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE traffic_db TO traffic_app;
\c traffic_db
GRANT ALL PRIVILEGES ON SCHEMA public TO traffic_app;
\q
```

### macOS Setup (Homebrew)

```bash
# Install PostgreSQL
brew install postgresql@15

# Start service
brew services start postgresql@15

# Create database and user
createuser traffic_app
createdb -O traffic_app traffic_db

# Set password
psql postgres
ALTER USER traffic_app WITH PASSWORD 'your_secure_password';
\q
```

---

## Configuration

### 1. Environment Variables

Create `.env` file in project root:

```bash
# Database Configuration
DB_TYPE=postgresql
POSTGRES_USER=traffic_app
POSTGRES_PASSWORD=your_secure_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=traffic_db

# Optional: SQL logging for debugging
ECHO_SQL=false
```

### 2. Connect to Database in Python

```python
import os
from src.database.init import init_database_from_env

# Uses environment variables
db = init_database_from_env()
```

### 3. Connection String Examples

**SQLite (Development)**
```
sqlite:///traffic.db
```

**PostgreSQL (Production)**
```
postgresql://traffic_app:password@localhost:5432/traffic_db
```

**PostgreSQL (with pgBouncer Connection Pooling)**
```
postgresql://traffic_app:password@pgbouncer:6432/traffic_db
```

---

## Database Initialization

### From Python Application

```python
from src.database.init import DatabaseInitializer
from src.database.config import DatabaseConfig

# Create config
config = DatabaseConfig(
    db_type="postgresql",
    postgres_user="traffic_app",
    postgres_password="your_password",
    postgres_host="localhost",
    postgres_port=5432,
    postgres_db="traffic_db",
    pool_size=20,
    max_overflow=40,
    echo_sql=False
)

# Initialize
initializer = DatabaseInitializer(config)
success = initializer.initialize(drop_existing=False)

if success:
    print("Database initialized successfully")
    db = initializer.manager
```

### Verify Installation

```python
from src.database.init import init_database

db = init_database(db_type="postgresql")

# Get all lanes
lanes = db.get_all_lanes()
print(f"Database connected! Lanes: {len(lanes)}")
```

---

## Performance Tuning

### PostgreSQL Configuration (postgresql.conf)

**Location:**
- Windows: `C:\Program Files\PostgreSQL\15\data\postgresql.conf`
- Linux: `/etc/postgresql/15/main/postgresql.conf`
- macOS: `/usr/local/var/postgres/postgresql.conf`

**Recommended Settings (for traffic monitoring):**

```
# Memory Usage (tune based on system RAM)
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 64MB
maintenance_work_mem = 64MB

# Connections
max_connections = 100
max_wal_senders = 10

# Performance
random_page_cost = 1.1  # For SSD
effective_io_concurrency = 200

# Logging
log_min_duration_statement = 1000  # Log queries > 1 second
log_statement = 'all'  # Log all statements
```

### Connection Pooling

**Option 1: PgBouncer (Recommended)**

```bash
# Install
sudo apt install pgbouncer  # Linux
brew install pgbouncer      # macOS

# Configure /etc/pgbouncer/pgbouncer.ini
[databases]
traffic_db = host=localhost port=5432 dbname=traffic_db

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
min_pool_size = 5
reserve_pool_size = 5
reserve_pool_timeout = 3

# Start
pgbouncer -d /etc/pgbouncer/pgbouncer.ini
```

**Option 2: SQLAlchemy Pool Configuration**

```python
from src.database.config import DatabaseConfig

config = DatabaseConfig(
    db_type="postgresql",
    pool_size=20,           # Connections to keep in pool
    max_overflow=40,        # Extra connections allowed
)
```

---

## Backup and Recovery

### Automated Backups

**Windows (Using Task Scheduler)**

Create batch file `backup_db.bat`:
```batch
@echo off
setlocal enabledelayedexpansion

set PGPASSWORD=your_password
set BACKUP_DIR=C:\backups
set TIMESTAMP=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%

pg_dump -U traffic_app -h localhost traffic_db > %BACKUP_DIR%\traffic_db_%TIMESTAMP%.sql

echo Backup completed: %BACKUP_DIR%\traffic_db_%TIMESTAMP%.sql
```

Schedule in Task Scheduler to run daily.

**Linux (Using Cron)**

```bash
# Add to crontab (crontab -e)
# Backup daily at 2 AM
0 2 * * * /usr/bin/pg_dump -U traffic_app -h localhost traffic_db | gzip > /backups/traffic_db_$(date +\%Y\%m\%d).sql.gz
```

**Python Script (Automatic)**

```python
import subprocess
from datetime import datetime

def backup_database():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"traffic_db_{timestamp}.sql"
    
    with open(filename, 'w') as f:
        subprocess.run([
            'pg_dump',
            '-U', 'traffic_app',
            '-h', 'localhost',
            'traffic_db'
        ], stdout=f)
    
    print(f"Backup created: {filename}")

if __name__ == "__main__":
    backup_database()
```

### Manual Backup/Restore

```bash
# Backup
pg_dump -U traffic_app -h localhost traffic_db > backup.sql

# Backup with compression
pg_dump -U traffic_app -h localhost traffic_db | gzip > backup.sql.gz

# Restore
psql -U traffic_app -h localhost traffic_db < backup.sql

# Restore from compressed
gunzip < backup.sql.gz | psql -U traffic_app -h localhost traffic_db
```

---

## Monitoring

### Check Database Size

```bash
psql -U traffic_app -d traffic_db

# Inside psql:
SELECT pg_size_pretty(pg_database_size('traffic_db'));

# Table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

\q
```

### Monitor Connections

```bash
psql -U traffic_app -d traffic_db

# Active connections
SELECT pid, username, application_name, state, query 
FROM pg_stat_activity;

# Slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

\q
```

### Query Performance

```python
from src.database.config import DatabaseConfig

# Enable SQL logging
config = DatabaseConfig(echo_sql=True)  # See all SQL queries

# Analyze query plan
session = db.get_session()
explain = session.execute("EXPLAIN ANALYZE SELECT * FROM vehicle_detections LIMIT 10")
for row in explain:
    print(row)
```

---

## Maintenance Tasks

### Regular Maintenance

```bash
# Connect to database
psql -U traffic_app -d traffic_db

# Vacuum (cleanup)
VACUUM ANALYZE;

# Reindex (optimize indexes)
REINDEX DATABASE traffic_db;

# Analyze (update statistics)
ANALYZE;

\q
```

### Archive Old Data

```python
from datetime import datetime, timedelta
from src.database.manager import DatabaseManager

db = DatabaseManager(session_factory)

# Archive violations older than 90 days
cutoff = datetime.utcnow() - timedelta(days=90)

# Export to CSV before deleting
violations = db.get_violations(hours=90*24)
# ... export to CSV ...

# Delete (if archiving successful)
session = db.get_session()
session.query(ViolationRecord).filter(
    ViolationRecord.timestamp < cutoff
).delete()
session.commit()
```

---

## Troubleshooting

### Connection Failed

```bash
# Check PostgreSQL is running
ps aux | grep postgres  # Linux/macOS
tasklist | findstr postgres  # Windows

# Check port is open
netstat -an | grep 5432  # Linux/macOS
netstat -an | findstr 5432  # Windows

# Check logs
tail /var/log/postgresql/postgresql.log  # Linux
```

### Permission Denied

```bash
# Grant permissions again
psql -U postgres

ALTER ROLE traffic_app CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE traffic_db TO traffic_app;
\c traffic_db
GRANT ALL PRIVILEGES ON SCHEMA public TO traffic_app;
\q
```

### Disk Space Issues

```bash
# Check disk usage
df -h  # Linux/macOS

# Archive old data
# Use "Archive Old Data" script above

# Vacuum to reclaim space
psql -U traffic_app -d traffic_db -c "VACUUM FULL;"
```

### Too Many Connections

```bash
# Check active connections
psql -U traffic_app -d traffic_db -c "SELECT count(*) FROM pg_stat_activity;"

# Terminate idle connections
SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
WHERE state = 'idle' AND query_start < now() - interval '1 hour';

# Increase max connections in postgresql.conf
max_connections = 200
```

---

## Docker Deployment

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: traffic_app
      POSTGRES_PASSWORD: your_secure_password
      POSTGRES_DB: traffic_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U traffic_app"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build: .
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DB_TYPE: postgresql
      POSTGRES_USER: traffic_app
      POSTGRES_PASSWORD: your_secure_password
      POSTGRES_HOST: postgres
      POSTGRES_DB: traffic_db
    ports:
      - "8000:8000"

volumes:
  postgres_data:
```

Run:
```bash
docker-compose up -d
docker-compose logs -f
```

---

## Security Best Practices

1. **Strong Passwords**
   ```sql
   ALTER USER traffic_app WITH PASSWORD 'very_strong_password_here';
   ```

2. **Limit Connections**
   ```sql
   ALTER USER traffic_app CONNECTION LIMIT 50;
   ```

3. **Restrict Access (pg_hba.conf)**
   ```
   # Only allow local connections
   local   traffic_db  traffic_app    md5
   host    traffic_db  traffic_app    127.0.0.1/32  md5
   ```

4. **Rotate Backups**
   - Keep only last 30 days of backups
   - Encrypt backup files
   - Store off-site

5. **Monitor Activity**
   ```sql
   SELECT username, application_name, state, query 
   FROM pg_stat_activity;
   ```

6. **Regular Updates**
   ```bash
   # Check version
   psql --version
   
   # Update PostgreSQL regularly
   ```

---

## Example: Complete Setup Script

```bash
#!/bin/bash

# Create traffic database and user
PGPASSWORD=postgres_superuser_password psql -U postgres -h localhost << EOF

-- Create database
CREATE DATABASE traffic_db;

-- Create user
CREATE USER traffic_app WITH PASSWORD 'traffic_app_password';

-- Grant privileges
ALTER ROLE traffic_app CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE traffic_db TO traffic_app;

-- Connect to database
\c traffic_db

-- Grant schema privileges
GRANT ALL PRIVILEGES ON SCHEMA public TO traffic_app;

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

EOF

echo "PostgreSQL setup completed!"
```

Save as `setup_postgres.sh` and run:
```bash
chmod +x setup_postgres.sh
./setup_postgres.sh
```

---

## Next Steps

1. ✅ Install PostgreSQL
2. ✅ Create database and user  
3. ✅ Test connection
4. ✅ Configure environment variables
5. ✅ Run database initialization
6. ✅ Set up automated backups
7. ✅ Configure monitoring
8. ✅ Deploy application

**For detailed Python integration, see:** [DATABASE_INTEGRATION.md](DATABASE_INTEGRATION.md)
