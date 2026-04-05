-- Copyright (c) 2024 Traffic Management System
-- Initialize PostgreSQL database for traffic management system

-- Create schema
CREATE SCHEMA IF NOT EXISTS traffic;

-- Create lane dimension table
CREATE TABLE IF NOT EXISTS traffic.lanes (
    lane_id SERIAL PRIMARY KEY,
    lane_name VARCHAR(50) UNIQUE NOT NULL,
    direction VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create vehicle detection table
CREATE TABLE IF NOT EXISTS traffic.vehicle_detections (
    detection_id BIGSERIAL PRIMARY KEY,
    lane_id INTEGER NOT NULL REFERENCES traffic.lanes(lane_id),
    vehicle_id VARCHAR(50),
    timestamp TIMESTAMP NOT NULL,
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    x_min INTEGER,
    y_min INTEGER,
    x_max INTEGER,
    y_max INTEGER,
    speed FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lane_id) REFERENCES traffic.lanes(lane_id)
);

-- Create violation records table
CREATE TABLE IF NOT EXISTS traffic.violation_records (
    violation_id BIGSERIAL PRIMARY KEY,
    detection_id BIGINT NOT NULL REFERENCES traffic.vehicle_detections(detection_id),
    lane_id INTEGER NOT NULL REFERENCES traffic.lanes(lane_id),
    violation_type VARCHAR(50) NOT NULL,
    severity INTEGER CHECK (severity >= 1 AND severity <= 5),
    timestamp TIMESTAMP NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create wait time observations table
CREATE TABLE IF NOT EXISTS traffic.wait_time_observations (
    observation_id BIGSERIAL PRIMARY KEY,
    lane_id INTEGER NOT NULL REFERENCES traffic.lanes(lane_id),
    wait_time FLOAT NOT NULL,
    queue_length INTEGER,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create hourly statistics table
CREATE TABLE IF NOT EXISTS traffic.hourly_statistics (
    stat_id BIGSERIAL PRIMARY KEY,
    lane_id INTEGER NOT NULL REFERENCES traffic.lanes(lane_id),
    hour_start TIMESTAMP NOT NULL,
    vehicle_count INTEGER DEFAULT 0,
    avg_speed FLOAT,
    max_speed FLOAT,
    min_speed FLOAT,
    avg_wait_time FLOAT,
    violation_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create daily statistics table
CREATE TABLE IF NOT EXISTS traffic.daily_statistics (
    stat_id BIGSERIAL PRIMARY KEY,
    lane_id INTEGER NOT NULL REFERENCES traffic.lanes(lane_id),
    date DATE NOT NULL,
    vehicle_count INTEGER DEFAULT 0,
    avg_speed FLOAT,
    max_speed FLOAT,
    min_speed FLOAT,
    peak_hour INTEGER,
    total_violations INTEGER DEFAULT 0,
    avg_wait_time FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(lane_id, date)
);

-- Create signal state table
CREATE TABLE IF NOT EXISTS traffic.signal_states (
    state_id BIGSERIAL PRIMARY KEY,
    lane_id INTEGER NOT NULL REFERENCES traffic.lanes(lane_id),
    state VARCHAR(20) NOT NULL,
    duration INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create traffic snapshot table
CREATE TABLE IF NOT EXISTS traffic.traffic_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    total_vehicles INTEGER DEFAULT 0,
    avg_congestion FLOAT,
    system_health VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_vehicle_detections_lane_timestamp 
    ON traffic.vehicle_detections(lane_id, timestamp DESC);

CREATE INDEX idx_vehicle_detections_timestamp 
    ON traffic.vehicle_detections(timestamp DESC);

CREATE INDEX idx_violation_records_lane_timestamp 
    ON traffic.violation_records(lane_id, timestamp DESC);

CREATE INDEX idx_violation_records_processed 
    ON traffic.violation_records(processed, timestamp DESC);

CREATE INDEX idx_hourly_statistics_lane_hour 
    ON traffic.hourly_statistics(lane_id, hour_start DESC);

CREATE INDEX idx_daily_statistics_lane_date 
    ON traffic.daily_statistics(lane_id, date DESC);

CREATE INDEX idx_signal_states_lane_timestamp 
    ON traffic.signal_states(lane_id, timestamp DESC);

CREATE INDEX idx_traffic_snapshots_timestamp 
    ON traffic.traffic_snapshots(timestamp DESC);

-- Create views for analytics

-- Vehicle count by lane per hour
CREATE OR REPLACE VIEW traffic.v_vehicle_count_by_lane_hour AS
SELECT 
    l.lane_name,
    DATE_TRUNC('hour', vd.timestamp) as hour,
    COUNT(*) as vehicle_count,
    AVG(vd.speed) as avg_speed
FROM traffic.vehicle_detections vd
JOIN traffic.lanes l ON vd.lane_id = l.lane_id
GROUP BY l.lane_name, DATE_TRUNC('hour', vd.timestamp);

-- Violation summary by type
CREATE OR REPLACE VIEW traffic.v_violations_by_type AS
SELECT 
    violation_type,
    COUNT(*) as count,
    AVG(severity) as avg_severity
FROM traffic.violation_records
GROUP BY violation_type;

-- Lane congestion summary
CREATE OR REPLACE VIEW traffic.v_lane_congestion_summary AS
SELECT 
    l.lane_name,
    COUNT(vd.detection_id) as vehicle_count,
    AVG(vd.speed) as avg_speed,
    AVG(CASE WHEN vd.speed < 10 THEN 1 ELSE 0 END) as congestion_ratio
FROM traffic.lanes l
LEFT JOIN traffic.vehicle_detections vd 
    ON l.lane_id = vd.lane_id 
    AND vd.timestamp > NOW() - INTERVAL '1 hour'
GROUP BY l.lane_name;

-- Insert default lanes
INSERT INTO traffic.lanes (lane_name, direction) VALUES
    ('North', 'North'),
    ('South', 'South'),
    ('East', 'East'),
    ('West', 'West')
ON CONFLICT (lane_name) DO NOTHING;

-- Grant permissions to traffic_user
GRANT USAGE ON SCHEMA traffic TO traffic_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA traffic TO traffic_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA traffic TO traffic_user;
GRANT SELECT ON ALL VIEWS IN SCHEMA traffic TO traffic_user;
