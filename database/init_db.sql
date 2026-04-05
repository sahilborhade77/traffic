-- PART 3: Database Schema (PostgreSQL)

-- vehicles table (RTO registry)
CREATE TABLE IF NOT EXISTS vehicles (
    plate_number VARCHAR(20) PRIMARY KEY,
    owner_name VARCHAR(100) NOT NULL,
    owner_phone VARCHAR(15) NOT NULL,
    owner_email VARCHAR(100),
    vehicle_type VARCHAR(20), -- car, bike, truck, auto
    registration_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- violations table
CREATE TABLE IF NOT EXISTS violations (
    violation_id SERIAL PRIMARY KEY,
    plate_number VARCHAR(20) REFERENCES vehicles(plate_number),
    violation_type VARCHAR(50) NOT NULL, -- red_light, overspeeding, no_helmet, etc.
    camera_id VARCHAR(50) NOT NULL,
    location VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    
    -- Evidence
    image_path VARCHAR(255),
    video_path VARCHAR(255),
    confidence_score FLOAT,
    
    -- Violation-specific data (JSONB for flexibility)
    metadata JSONB, -- {speed: 85, limit: 60, distance: 2.5km}
    
    -- Fine information
    fine_amount DECIMAL(10, 2),
    fine_status VARCHAR(20) DEFAULT 'pending', -- pending, paid, disputed, cancelled
    
    -- Review
    reviewed BOOLEAN DEFAULT FALSE,
    reviewer_notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- speed_tracking table (for average speed enforcement)
CREATE TABLE IF NOT EXISTS speed_tracking (
    tracking_id SERIAL PRIMARY KEY,
    plate_number VARCHAR(20),
    entry_camera VARCHAR(50) NOT NULL,
    entry_timestamp TIMESTAMP NOT NULL,
    exit_camera VARCHAR(50),
    exit_timestamp TIMESTAMP,
    
    -- Calculated fields
    distance_km DECIMAL(5, 2),
    time_taken_seconds INT,
    average_speed_kmh DECIMAL(5, 2),
    speed_limit_kmh INT,
    
    -- Status
    is_violation BOOLEAN DEFAULT FALSE,
    violation_id INT REFERENCES violations(violation_id),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- camera_config table
CREATE TABLE IF NOT EXISTS camera_config (
    camera_id VARCHAR(50) PRIMARY KEY,
    location VARCHAR(100) NOT NULL,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    camera_type VARCHAR(20), -- entry, exit, junction
    paired_camera VARCHAR(50), -- for speed enforcement pairs
    distance_to_pair_km DECIMAL(5, 2),
    speed_limit_kmh INT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- fine_rules table
CREATE TABLE IF NOT EXISTS fine_rules (
    rule_id SERIAL PRIMARY KEY,
    violation_type VARCHAR(50) UNIQUE NOT NULL,
    base_fine DECIMAL(10, 2) NOT NULL,
    description TEXT,
    severity VARCHAR(20), -- minor, moderate, severe
    repeat_multiplier DECIMAL(3, 2) DEFAULT 1.5, -- 50% increase for repeat offenders
    is_active BOOLEAN DEFAULT TRUE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_violations_plate ON violations(plate_number);
CREATE INDEX IF NOT EXISTS idx_violations_timestamp ON violations(timestamp);
CREATE INDEX IF NOT EXISTS idx_violations_status ON violations(fine_status);
CREATE INDEX IF NOT EXISTS idx_speed_tracking_plate ON speed_tracking(plate_number);
CREATE INDEX IF NOT EXISTS idx_speed_tracking_entry ON speed_tracking(entry_timestamp);
