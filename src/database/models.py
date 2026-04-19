from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean,
    ForeignKey, Text, JSON, Numeric, Index, func, Enum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

# ========== ENUMS ==========

class VehicleClass(enum.Enum):
    CAR = "car"
    MOTORCYCLE = "motorcycle"
    BUS = "bus"
    TRUCK = "truck"
    AUTO = "auto_rickshaw"
    BICYCLE = "bicycle"
    PEDESTRIAN = "pedestrian"
    OTHER = "other"

class ViolationType(enum.Enum):
    RED_LIGHT = "red_light"
    OVERSPEEDING = "overspeeding"
    WRONG_WAY = "wrong_way"
    TRIPLE_RIDING = "triple_riding"
    PHONE_USE = "phone_use"
    NO_HELMET = "no_helmet"
    WRONG_LANE = "wrong_lane"
    OTHER = "other"

class ViolationSeverity(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class CongestionLevel(enum.Enum):
    LOW = "low"
    MODERATE = "moderate"
    HEAVY = "heavy"
    CRITICAL = "critical"

# ========== MODELS ==========

class Lane(Base):
    __tablename__ = "lanes"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    direction = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())

class Vehicle(Base):
    """RTO Registry for vehicles."""
    __tablename__ = "vehicles"
    plate_number = Column(String(20), primary_key=True)
    owner_name = Column(String(100), nullable=False)
    owner_phone = Column(String(15), nullable=False)
    owner_email = Column(String(100))
    vehicle_type = Column(String(20))
    registration_date = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

class VehicleDetection(Base):
    """Individual vehicle detections per frame."""
    __tablename__ = "vehicle_detections"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    frame_id = Column(Integer)
    vehicle_id = Column(Integer)
    lane_id = Column(Integer, ForeignKey("lanes.id"))
    vehicle_class = Column(Enum(VehicleClass), default=VehicleClass.OTHER)
    confidence = Column(Float)
    speed = Column(Float)
    distance = Column(Float)
    position_x = Column(Float)
    position_y = Column(Float)
    bbox_x1 = Column(Integer)
    bbox_y1 = Column(Integer)
    bbox_x2 = Column(Integer)
    bbox_y2 = Column(Integer)
    custom_metadata = Column(JSON)

class Violation(Base):
    """Traffic violation records (also known as ViolationRecord)."""
    __tablename__ = "violations"
    violation_id = Column(Integer, primary_key=True)
    plate_number = Column(String(20), ForeignKey("vehicles.plate_number"), index=True)
    violation_type = Column(String(50), nullable=False)
    camera_id = Column(String(50), nullable=False)
    location = Column(String(100), nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    image_path = Column(String(255))
    video_path = Column(String(255))
    confidence_score = Column(Float)
    metadata_json = Column(JSON)
    fine_amount = Column(Numeric(10, 2))
    fine_status = Column(String(20), default='pending', index=True)
    reviewed = Column(Boolean, default=False)
    reviewer_notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

# Alias for legacy code support
ViolationRecord = Violation

class WaitTimeObservation(Base):
    __tablename__ = "wait_times"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    lane_id = Column(Integer, ForeignKey("lanes.id"))
    vehicle_id = Column(Integer)
    vehicle_type = Column(Enum(VehicleClass), default=VehicleClass.OTHER)
    wait_time_seconds = Column(Float)
    entry_time = Column(DateTime)
    exit_time = Column(DateTime)
    stopped_duration = Column(Float)
    custom_metadata = Column(JSON)

class HourlyStatistic(Base):
    __tablename__ = "hourly_statistics"
    id = Column(Integer, primary_key=True)
    datetime = Column(DateTime, default=datetime.utcnow, index=True)
    hour = Column(Integer)
    lane_id = Column(Integer, ForeignKey("lanes.id"))
    total_vehicles = Column(Integer)
    vehicle_breakdown = Column(JSON)
    avg_wait_time = Column(Float)
    max_wait_time = Column(Float)
    min_wait_time = Column(Float)
    total_violations = Column(Integer)
    peak_hour = Column(Boolean, default=False)
    avg_vehicle_speed = Column(Float)
    traffic_density = Column(Float)
    congestion_level = Column(Enum(CongestionLevel), default=CongestionLevel.LOW)
    custom_metadata = Column(JSON)

class DailyStatistic(Base):
    __tablename__ = "daily_statistics"
    id = Column(Integer, primary_key=True)
    date = Column(String(10), index=True)
    day_of_week = Column(String(15))
    lane_id = Column(Integer, ForeignKey("lanes.id"))
    total_vehicles = Column(Integer)
    vehicle_breakdown = Column(JSON)
    avg_wait_time = Column(Float)
    peak_hours = Column(JSON)
    total_violations = Column(Integer)
    avg_traffic_density = Column(Float)
    avg_vehicle_speed = Column(Float)
    busiest_hour = Column(Integer)
    custom_metadata = Column(JSON)

class SignalState(Base):
    __tablename__ = "signal_states"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    lane_id = Column(Integer, ForeignKey("lanes.id"))
    state = Column(String(20)) # red, green, yellow
    duration = Column(Float)
    adaptive_mode = Column(Boolean, default=False)
    queue_length = Column(Integer)
    response_time = Column(Float)
    custom_metadata = Column(JSON)

class TrafficSnapshot(Base):
    __tablename__ = "traffic_snapshots"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    lane_id = Column(Integer, ForeignKey("lanes.id"))
    active_vehicles = Column(Integer)
    congestion_level = Column(Enum(CongestionLevel), default=CongestionLevel.LOW)
    avg_speed = Column(Float)
    violations_count = Column(Integer)
    avg_wait_time = Column(Float)
    signal_state = Column(String(20))
    custom_metadata = Column(JSON)

class SpeedTracking(Base):
    """Tracking for average speed enforcement across camera pairs."""
    __tablename__ = "speed_tracking"
    tracking_id = Column(Integer, primary_key=True)
    plate_number = Column(String(20), index=True)
    entry_camera = Column(String(50), nullable=False)
    entry_timestamp = Column(DateTime, nullable=False, index=True)
    exit_camera = Column(String(50))
    exit_timestamp = Column(DateTime)
    distance_km = Column(Numeric(5, 2))
    time_taken_seconds = Column(Integer)
    average_speed_kmh = Column(Numeric(5, 2))
    speed_limit_kmh = Column(Integer)
    is_violation = Column(Boolean, default=False)
    violation_id = Column(Integer, ForeignKey("violations.violation_id"))
    created_at = Column(DateTime, server_default=func.now())

class CameraConfig(Base):
    __tablename__ = "camera_config"
    camera_id = Column(String(50), primary_key=True)
    location = Column(String(100), nullable=False)
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(11, 8))
    camera_type = Column(String(20))
    paired_camera = Column(String(50))
    distance_to_pair_km = Column(Numeric(5, 2))
    speed_limit_kmh = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

class FineRule(Base):
    __tablename__ = "fine_rules"
    rule_id = Column(Integer, primary_key=True)
    violation_type = Column(String(50), unique=True, nullable=False)
    base_fine = Column(Numeric(10, 2), nullable=False)
    description = Column(Text)
    severity = Column(String(20))
    repeat_multiplier = Column(Numeric(3, 2), default=1.5)
    is_active = Column(Boolean, default=True)
