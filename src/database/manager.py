"""
Database manager for handling all database operations.

Provides high-level APIs for:
- Vehicle detection CRUD
- Violation recording and queries
- Wait time tracking
- Statistics aggregation and retrieval
- Signal state management
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc

from src.database.models import (
    Lane,
    VehicleDetection,
    ViolationRecord,
    WaitTimeObservation,
    HourlyStatistic,
    DailyStatistic,
    SignalState,
    TrafficSnapshot,
    VehicleClass,
    ViolationType,
    ViolationSeverity,
    CongestionLevel,
)


class DatabaseManager:
    """High-level database manager."""

    def __init__(self, session_factory):
        """
        Initialize database manager.

        Args:
            session_factory: SQLAlchemy sessionmaker instance
        """
        self.session_factory = session_factory

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.session_factory()

    # ========== LANE MANAGEMENT ==========

    def get_or_create_lane(self, name: str, direction: Optional[str] = None) -> Lane:
        """Get or create a lane."""
        session = self.get_session()
        try:
            lane = session.query(Lane).filter(Lane.name == name).first()
            if not lane:
                lane = Lane(name=name, direction=direction or name)
                session.add(lane)
                session.commit()
            return lane
        finally:
            session.close()

    def get_all_lanes(self) -> List[Lane]:
        """Get all lanes."""
        session = self.get_session()
        try:
            return session.query(Lane).all()
        finally:
            session.close()

    # ========== VEHICLE DETECTION OPERATIONS ==========

    def add_vehicle_detection(
        self,
        lane_name: str,
        vehicle_id: int,
        vehicle_class: str,
        speed: float,
        frame_id: Optional[int] = None,
        confidence: float = 0.0,
        distance: Optional[float] = None,
        position_x: Optional[float] = None,
        position_y: Optional[float] = None,
        bbox: Optional[tuple] = None,
        metadata: Optional[Dict] = None,
        timestamp: Optional[datetime] = None,
    ) -> VehicleDetection:
        """
        Record a vehicle detection.

        Args:
            lane_name: Lane name
            vehicle_id: Detection vehicle ID
            vehicle_class: Vehicle class (car, truck, etc.)
            speed: Vehicle speed in m/s
            frame_id: Video frame ID
            confidence: Detection confidence score
            distance: Distance traveled
            position_x: X coordinate
            position_y: Y coordinate
            bbox: Bounding box (x1, y1, x2, y2)
            metadata: Additional metadata
            timestamp: Detection timestamp

        Returns:
            VehicleDetection record
        """
        session = self.get_session()
        try:
            lane = self.get_or_create_lane(lane_name)

            # Parse vehicle class
            try:
                v_class = VehicleClass(vehicle_class.lower())
            except ValueError:
                v_class = VehicleClass.OTHER

            detection = VehicleDetection(
                timestamp=timestamp or datetime.utcnow(),
                frame_id=frame_id,
                vehicle_id=vehicle_id,
                lane_id=lane.id,
                vehicle_class=v_class,
                confidence=confidence,
                speed=speed,
                distance=distance,
                position_x=position_x,
                position_y=position_y,
                bbox_x1=bbox[0] if bbox else None,
                bbox_y1=bbox[1] if bbox else None,
                bbox_x2=bbox[2] if bbox else None,
                bbox_y2=bbox[3] if bbox else None,
                custom_metadata=metadata or {},
            )
            session.add(detection)
            session.commit()
            return detection
        finally:
            session.close()

    def get_vehicle_detections(
        self,
        lane_name: Optional[str] = None,
        hours: int = 1,
        limit: int = 1000,
    ) -> List[VehicleDetection]:
        """Get recent vehicle detections."""
        session = self.get_session()
        try:
            query = session.query(VehicleDetection)

            if lane_name:
                lane = session.query(Lane).filter(Lane.name == lane_name).first()
                if lane:
                    query = query.filter(VehicleDetection.lane_id == lane.id)

            # Filter by time
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            query = query.filter(VehicleDetection.timestamp >= cutoff_time)

            return query.order_by(desc(VehicleDetection.timestamp)).limit(limit).all()
        finally:
            session.close()

    def get_vehicle_speed_stats(self, lane_name: str, hours: int = 1) -> Dict[str, float]:
        """Get speed statistics for a lane."""
        session = self.get_session()
        try:
            lane = session.query(Lane).filter(Lane.name == lane_name).first()
            if not lane:
                return {}

            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            detections = session.query(VehicleDetection).filter(
                and_(
                    VehicleDetection.lane_id == lane.id,
                    VehicleDetection.timestamp >= cutoff_time,
                )
            ).all()

            if not detections:
                return {}

            speeds = [d.speed for d in detections if d.speed]
            return {
                "avg": sum(speeds) / len(speeds),
                "min": min(speeds),
                "max": max(speeds),
                "count": len(detections),
            }
        finally:
            session.close()

    # ========== VIOLATION OPERATIONS ==========

    def record_violation(
        self,
        lane_name: str,
        violation_type: str,
        vehicle_id: int,
        severity: str = "medium",
        description: Optional[str] = None,
        signal_state: Optional[str] = None,
        vehicle_speed: Optional[float] = None,
        speed_limit: Optional[float] = None,
        snapshot_path: Optional[str] = None,
        evidence_data: Optional[Dict] = None,
        timestamp: Optional[datetime] = None,
    ) -> ViolationRecord:
        """
        Record a traffic violation.

        Args:
            lane_name: Lane where violation occurred
            violation_type: Type of violation
            vehicle_id: Vehicle ID
            severity: Severity level
            description: Description
            signal_state: Signal state at violation
            vehicle_speed: Vehicle speed at violation
            speed_limit: Speed limit
            snapshot_path: Path to snapshot
            evidence_data: Additional evidence
            timestamp: Violation timestamp

        Returns:
            ViolationRecord
        """
        session = self.get_session()
        try:
            lane = self.get_or_create_lane(lane_name)

            # Parse violation type and severity
            try:
                v_type = ViolationType(violation_type.lower())
            except ValueError:
                v_type = ViolationType.OTHER

            try:
                v_severity = ViolationSeverity(severity.lower())
            except ValueError:
                v_severity = ViolationSeverity.MEDIUM

            violation = ViolationRecord(
                timestamp=timestamp or datetime.utcnow(),
                lane_id=lane.id,
                vehicle_id=vehicle_id,
                violation_type=v_type,
                severity=v_severity,
                description=description,
                signal_state=signal_state,
                vehicle_speed=vehicle_speed,
                speed_limit=speed_limit,
                snapshot_path=snapshot_path,
                custom_metadata=evidence_data or {},
            )
            session.add(violation)
            session.commit()
            return violation
        finally:
            session.close()

    def get_violations(
        self,
        lane_name: Optional[str] = None,
        violation_type: Optional[str] = None,
        hours: int = 24,
        limit: int = 100,
    ) -> List[ViolationRecord]:
        """Get violations with filters."""
        session = self.get_session()
        try:
            query = session.query(ViolationRecord)

            if lane_name:
                lane = session.query(Lane).filter(Lane.name == lane_name).first()
                if lane:
                    query = query.filter(ViolationRecord.lane_id == lane.id)

            if violation_type:
                try:
                    v_type = ViolationType(violation_type.lower())
                    query = query.filter(ViolationRecord.violation_type == v_type)
                except ValueError:
                    pass

            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            query = query.filter(ViolationRecord.timestamp >= cutoff_time)

            return query.order_by(desc(ViolationRecord.timestamp)).limit(limit).all()
        finally:
            session.close()

    def get_violation_summary(
        self, lane_name: Optional[str] = None, days: int = 7
    ) -> Dict[str, Any]:
        """Get violation summary statistics."""
        session = self.get_session()
        try:
            query = session.query(ViolationRecord)

            if lane_name:
                lane = session.query(Lane).filter(Lane.name == lane_name).first()
                if lane:
                    query = query.filter(ViolationRecord.lane_id == lane.id)

            cutoff_time = datetime.utcnow() - timedelta(days=days)
            query = query.filter(ViolationRecord.timestamp >= cutoff_time)

            violations = query.all()

            return {
                "total": len(violations),
                "by_type": self._group_by_field(violations, "violation_type"),
                "by_severity": self._group_by_field(violations, "severity"),
                "critical_count": sum(1 for v in violations if v.severity == ViolationSeverity.CRITICAL),
            }
        finally:
            session.close()

    # ========== WAIT TIME OPERATIONS ==========

    def record_wait_time(
        self,
        lane_name: str,
        vehicle_id: int,
        vehicle_type: str,
        wait_time_seconds: float,
        entry_time: Optional[datetime] = None,
        exit_time: Optional[datetime] = None,
        stopped_duration: Optional[float] = None,
        metadata: Optional[Dict] = None,
        timestamp: Optional[datetime] = None,
    ) -> WaitTimeObservation:
        """Record a vehicle wait time."""
        session = self.get_session()
        try:
            lane = self.get_or_create_lane(lane_name)

            try:
                v_type = VehicleClass(vehicle_type.lower())
            except ValueError:
                v_type = VehicleClass.OTHER

            observation = WaitTimeObservation(
                timestamp=timestamp or datetime.utcnow(),
                lane_id=lane.id,
                vehicle_id=vehicle_id,
                vehicle_type=v_type,
                wait_time_seconds=wait_time_seconds,
                entry_time=entry_time,
                exit_time=exit_time,
                stopped_duration=stopped_duration,
                custom_metadata=metadata or {},
            )
            session.add(observation)
            session.commit()
            return observation
        finally:
            session.close()

    def get_wait_time_stats(self, lane_name: str, hours: int = 1) -> Dict[str, float]:
        """Get wait time statistics for a lane."""
        session = self.get_session()
        try:
            lane = session.query(Lane).filter(Lane.name == lane_name).first()
            if not lane:
                return {}

            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            observations = session.query(WaitTimeObservation).filter(
                and_(
                    WaitTimeObservation.lane_id == lane.id,
                    WaitTimeObservation.timestamp >= cutoff_time,
                )
            ).all()

            if not observations:
                return {}

            times = [o.wait_time_seconds for o in observations]
            return {
                "avg": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
                "count": len(observations),
            }
        finally:
            session.close()

    # ========== STATISTICS OPERATIONS ==========

    def store_hourly_statistic(
        self,
        lane_name: str,
        hour: int,
        total_vehicles: int,
        vehicle_breakdown: Dict,
        avg_wait_time: float,
        max_wait_time: float,
        min_wait_time: float,
        total_violations: int,
        peak_hour: bool = False,
        avg_vehicle_speed: float = 0.0,
        traffic_density: float = 0.0,
        congestion_level: str = "low",
        metadata: Optional[Dict] = None,
    ) -> HourlyStatistic:
        """Store hourly statistics."""
        session = self.get_session()
        try:
            lane = self.get_or_create_lane(lane_name)

            try:
                cong_level = CongestionLevel(congestion_level.lower())
            except ValueError:
                cong_level = CongestionLevel.LOW

            stat = HourlyStatistic(
                datetime=datetime.utcnow(),
                hour=hour,
                lane_id=lane.id,
                total_vehicles=total_vehicles,
                vehicle_breakdown=vehicle_breakdown,
                avg_wait_time=avg_wait_time,
                max_wait_time=max_wait_time,
                min_wait_time=min_wait_time,
                total_violations=total_violations,
                peak_hour=peak_hour,
                avg_vehicle_speed=avg_vehicle_speed,
                traffic_density=traffic_density,
                congestion_level=cong_level,
                custom_metadata=metadata or {},
            )
            session.add(stat)
            session.commit()
            return stat
        finally:
            session.close()

    def store_daily_statistic(
        self,
        lane_name: str,
        date: str,
        day_of_week: str,
        total_vehicles: int,
        vehicle_breakdown: Dict,
        avg_wait_time: float,
        peak_hours: List[int],
        total_violations: int,
        avg_traffic_density: float = 0.0,
        avg_vehicle_speed: float = 0.0,
        busiest_hour: Optional[int] = None,
        metadata: Optional[Dict] = None,
    ) -> DailyStatistic:
        """Store daily statistics."""
        session = self.get_session()
        try:
            lane = self.get_or_create_lane(lane_name)

            stat = DailyStatistic(
                date=date,
                day_of_week=day_of_week,
                lane_id=lane.id,
                total_vehicles=total_vehicles,
                vehicle_breakdown=vehicle_breakdown,
                avg_wait_time=avg_wait_time,
                peak_hours=peak_hours,
                total_violations=total_violations,
                avg_traffic_density=avg_traffic_density,
                avg_vehicle_speed=avg_vehicle_speed,
                busiest_hour=busiest_hour,
                custom_metadata=metadata or {},
            )
            session.add(stat)
            session.commit()
            return stat
        finally:
            session.close()

    def get_hourly_statistics(
        self, lane_name: Optional[str] = None, hours: int = 24, limit: int = 100
    ) -> List[HourlyStatistic]:
        """Get hourly statistics."""
        session = self.get_session()
        try:
            query = session.query(HourlyStatistic)

            if lane_name:
                lane = session.query(Lane).filter(Lane.name == lane_name).first()
                if lane:
                    query = query.filter(HourlyStatistic.lane_id == lane.id)

            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            query = query.filter(HourlyStatistic.datetime >= cutoff_time)

            return query.order_by(desc(HourlyStatistic.datetime)).limit(limit).all()
        finally:
            session.close()

    def get_daily_statistics(
        self, lane_name: Optional[str] = None, days: int = 30, limit: int = 365
    ) -> List[DailyStatistic]:
        """Get daily statistics."""
        session = self.get_session()
        try:
            query = session.query(DailyStatistic)

            if lane_name:
                lane = session.query(Lane).filter(Lane.name == lane_name).first()
                if lane:
                    query = query.filter(DailyStatistic.lane_id == lane.id)

            cutoff_date = (datetime.utcnow() - timedelta(days=days)).date()
            query = query.filter(DailyStatistic.date >= str(cutoff_date))

            return query.order_by(desc(DailyStatistic.date)).limit(limit).all()
        finally:
            session.close()

    # ========== SIGNAL STATE OPERATIONS ==========

    def record_signal_state(
        self,
        lane_name: str,
        state: str,
        duration: Optional[float] = None,
        adaptive_mode: bool = False,
        queue_length: Optional[int] = None,
        response_time: Optional[float] = None,
        metadata: Optional[Dict] = None,
        timestamp: Optional[datetime] = None,
    ) -> SignalState:
        """Record a signal state change."""
        session = self.get_session()
        try:
            lane = self.get_or_create_lane(lane_name)

            signal = SignalState(
                timestamp=timestamp or datetime.utcnow(),
                lane_id=lane.id,
                state=state.lower(),
                duration=duration,
                adaptive_mode=adaptive_mode,
                queue_length=queue_length,
                response_time=response_time,
                custom_metadata=metadata or {},
            )
            session.add(signal)
            session.commit()
            return signal
        finally:
            session.close()

    # ========== SNAPSHOT OPERATIONS ==========

    def record_snapshot(
        self,
        lane_name: str,
        active_vehicles: int,
        congestion_level: str = "low",
        avg_speed: Optional[float] = None,
        violations_count: int = 0,
        avg_wait_time: Optional[float] = None,
        signal_state: Optional[str] = None,
        metadata: Optional[Dict] = None,
        timestamp: Optional[datetime] = None,
    ) -> TrafficSnapshot:
        """Record a traffic snapshot."""
        session = self.get_session()
        try:
            lane = self.get_or_create_lane(lane_name)

            try:
                cong = CongestionLevel(congestion_level.lower())
            except ValueError:
                cong = CongestionLevel.LOW

            snapshot = TrafficSnapshot(
                timestamp=timestamp or datetime.utcnow(),
                lane_id=lane.id,
                active_vehicles=active_vehicles,
                congestion_level=cong,
                avg_speed=avg_speed,
                violations_count=violations_count,
                avg_wait_time=avg_wait_time,
                signal_state=signal_state,
                custom_metadata=metadata or {},
            )
            session.add(snapshot)
            session.commit()
            return snapshot
        finally:
            session.close()

    # ========== UTILITY METHODS ==========

    def _group_by_field(self, records: List, field_name: str) -> Dict[str, int]:
        """Group records by a field and count."""
        grouped = {}
        for record in records:
            value = getattr(record, field_name)
            if hasattr(value, 'value'):  # Enum
                value = value.value
            grouped[value] = grouped.get(value, 0) + 1
        return grouped

    def create_tables(self, engine):
        """Create all tables."""
        from src.database.models import Base
        Base.metadata.create_all(engine)

    def drop_all_tables(self, engine):
        """Drop all tables (careful!)."""
        from src.database.models import Base
        Base.metadata.drop_all(engine)
