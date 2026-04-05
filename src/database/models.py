from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean,
    ForeignKey, Text, JSON, Numeric, Index, func
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Vehicle(Base):
    """
    RTO Registry for vehicles.
    """
    __tablename__ = "vehicles"

    plate_number = Column(String(20), primary_key=True)
    owner_name = Column(String(100), nullable=False)
    owner_phone = Column(String(15), nullable=False)
    owner_email = Column(String(100))
    vehicle_type = Column(String(20)) # car, bike, truck, auto
    registration_date = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    violations = relationship("Violation", back_populates="vehicle")

    def __repr__(self):
        return f"<Vehicle(plate='{self.plate_number}', owner='{self.owner_name}')>"

class Violation(Base):
    """
    Traffic violation records.
    """
    __tablename__ = "violations"

    violation_id = Column(Integer, primary_key=True)
    plate_number = Column(String(20), ForeignKey("vehicles.plate_number"), index=True)
    violation_type = Column(String(50), nullable=False) # red_light, overspeeding, etc.
    camera_id = Column(String(50), nullable=False)
    location = Column(String(100), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Evidence
    image_path = Column(String(255))
    video_path = Column(String(255))
    confidence_score = Column(Float)
    
    # Violation-specific data
    metadata_json = Column(JSON) # {speed: 85, limit: 60, ...}
    
    # Fine information
    fine_amount = Column(Numeric(10, 2))
    fine_status = Column(String(20), default='pending', index=True) # pending, paid, etc.
    
    # Review
    reviewed = Column(Boolean, default=False)
    reviewer_notes = Column(Text)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    vehicle = relationship("Vehicle", back_populates="violations")

    def __repr__(self):
        return f"<Violation(id={self.violation_id}, plate='{self.plate_number}', type='{self.violation_type}')>"

class SpeedTracking(Base):
    """
    Tracking for average speed enforcement across camera pairs.
    """
    __tablename__ = "speed_tracking"

    tracking_id = Column(Integer, primary_key=True)
    plate_number = Column(String(20), index=True)
    entry_camera = Column(String(50), nullable=False)
    entry_timestamp = Column(DateTime, nullable=False, index=True)
    exit_camera = Column(String(50))
    exit_timestamp = Column(DateTime)
    
    # Calculated fields
    distance_km = Column(Numeric(5, 2))
    time_taken_seconds = Column(Integer)
    average_speed_kmh = Column(Numeric(5, 2))
    speed_limit_kmh = Column(Integer)
    
    # Status
    is_violation = Column(Boolean, default=False)
    violation_id = Column(Integer, ForeignKey("violations.violation_id"))
    
    created_at = Column(DateTime, server_default=func.now())

class CameraConfig(Base):
    """
    Camera infrastructure configuration.
    """
    __tablename__ = "camera_config"

    camera_id = Column(String(50), primary_key=True)
    location = Column(String(100), nullable=False)
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(11, 8))
    camera_type = Column(String(20)) # entry, exit, junction
    paired_camera = Column(String(50)) # for speed enforcement pairs
    distance_to_pair_km = Column(Numeric(5, 2))
    speed_limit_kmh = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

class FineRule(Base):
    """
    Rules for calculating fine amounts.
    """
    __tablename__ = "fine_rules"

    rule_id = Column(Integer, primary_key=True)
    violation_type = Column(String(50), unique=True, nullable=False)
    base_fine = Column(Numeric(10, 2), nullable=False)
    description = Column(Text)
    severity = Column(String(20)) # minor, moderate, severe
    repeat_multiplier = Column(Numeric(3, 2), default=1.5)
    is_active = Column(Boolean, default=True)
