"""Legacy-compatible red-light violation helpers used by older tests.

The production pipeline uses ``src.violations.red_light_detector``. This module
keeps the original vision-layer API available for tests and demos that still
exercise intersection-zone workflows.
"""

import csv
import json
import math
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import cv2
import numpy as np


@dataclass
class RedLightViolation:
    violation_id: str
    track_id: int
    vehicle_class: str
    lane_name: str
    timestamp: str
    unix_timestamp: float
    position: Tuple[float, float]
    vehicle_speed: float
    vehicle_direction: float
    signal_status: str
    crossing_confidence: float
    frame_number: int
    snapshot_path: str

    def to_dict(self):
        return asdict(self)


class ViolationStore(list):
    """List that also exposes ``values()`` for older dict-style callers."""

    def values(self):
        return list(self)


class IntersectionZoneManager:
    def __init__(self):
        self.tracking_zones: Dict[str, np.ndarray] = {}
        self.stop_lines: Dict[str, Tuple[Tuple[int, int], Tuple[int, int]]] = {}
        self.crossing_directions: Dict[str, Tuple[float, float]] = {}
        self.lane_positions: Dict[str, Tuple[int, int]] = {}

    def define_tracking_zone(self, lane_name: str, polygon: np.ndarray):
        self.tracking_zones[lane_name] = polygon

    def define_stop_line(self, lane_name: str, start, end, crossing_direction=(0, 1)):
        self.stop_lines[lane_name] = (tuple(start), tuple(end))
        self.crossing_directions[lane_name] = tuple(crossing_direction)

    def define_lane_position(self, lane_name: str, position):
        self.lane_positions[lane_name] = tuple(position)

    def is_point_in_zone(self, lane_name: str, x: float, y: float) -> bool:
        polygon = self.tracking_zones.get(lane_name)
        if polygon is None:
            return False
        return cv2.pointPolygonTest(polygon.astype(np.int32), (float(x), float(y)), False) >= 0

    def crosses_stop_line(self, lane_name: str, prev_pos, curr_pos) -> bool:
        line = self.stop_lines.get(lane_name)
        if line is None:
            return False
        return _segments_intersect(prev_pos, curr_pos, line[0], line[1])

    def get_crossing_direction(self, lane_name: str, prev_pos, curr_pos):
        if lane_name not in self.stop_lines:
            return None
        dx = curr_pos[0] - prev_pos[0]
        dy = curr_pos[1] - prev_pos[1]
        norm = math.hypot(dx, dy)
        if norm == 0:
            return (0.0, 0.0)
        return (dx / norm, dy / norm)


class RedLightViolationDetector:
    def __init__(self, zone_manager: Optional[IntersectionZoneManager] = None,
                 snapshot_dir: str = "data/violations/snapshots",
                 framerate: float = 30.0):
        self.zone_manager = zone_manager or IntersectionZoneManager()
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.framerate = framerate
        self.signal_state: Dict[str, str] = {}
        self.violations = ViolationStore()
        self.violation_count = 0
        self.violations_by_lane = Counter()
        self.violations_by_class = Counter()

    def update_signal_state(self, signal_state: Dict[str, str]):
        self.signal_state = signal_state or {}

    def create_violation(self, track, lane_name: str, frame: np.ndarray, frame_number: int):
        cx, cy = track.get_centroid()
        vehicle_class = getattr(track, "vehicle_class", "car")
        speed = track.calculate_speed(fps=self.framerate) or 0.0
        direction = track.calculate_direction() or 0.0
        violation_id = f"{lane_name}_{track.track_id}_{frame_number}"
        snapshot_path = self._save_snapshot(frame, violation_id)
        violation = RedLightViolation(
            violation_id=violation_id,
            track_id=track.track_id,
            vehicle_class=vehicle_class,
            lane_name=lane_name,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            unix_timestamp=time.time(),
            position=(float(cx), float(cy)),
            vehicle_speed=float(speed),
            vehicle_direction=float(direction),
            signal_status=self.signal_state.get(lane_name, "RED"),
            crossing_confidence=0.95,
            frame_number=frame_number,
            snapshot_path=snapshot_path
        )
        self._record_violation(violation)
        return violation

    def detect_violations(self, active_tracks: Dict[int, object], frame: np.ndarray, frame_number: int):
        detected = []
        for track in active_tracks.values():
            cx, cy = track.get_centroid()
            for lane_name in self.zone_manager.tracking_zones:
                if self.signal_state.get(lane_name) != "RED":
                    continue
                if self.zone_manager.is_point_in_zone(lane_name, cx, cy):
                    detected.append(self.create_violation(track, lane_name, frame, frame_number))
        return detected

    def draw_violations(self, frame, draw_zones=True, draw_stats=True):
        annotated = frame.copy()
        if draw_zones:
            for polygon in self.zone_manager.tracking_zones.values():
                cv2.polylines(annotated, [polygon.astype(np.int32)], True, (0, 255, 255), 2)
            for start, end in self.zone_manager.stop_lines.values():
                cv2.line(annotated, start, end, (0, 0, 255), 2)
        if draw_stats:
            cv2.putText(annotated, f"Violations: {self.violation_count}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return annotated

    def get_statistics(self):
        return {
            "total_violations": self.violation_count,
            "violations_by_lane": dict(self.violations_by_lane),
            "violations_by_class": dict(self.violations_by_class),
        }

    def get_violations_for_lane(self, lane_name: str) -> List[RedLightViolation]:
        return [v for v in _iter_violations(self.violations) if v.lane_name == lane_name]

    def export_violations(self, output_dir: str):
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        rows = [v.to_dict() for v in _iter_violations(self.violations)]
        json_path = output / "red_light_violations.json"
        csv_path = output / "red_light_violations.csv"
        json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ["violation_id"])
            writer.writeheader()
            writer.writerows(rows)
        return str(json_path), str(csv_path)

    def reset(self):
        self.violations = ViolationStore()
        self.violation_count = 0
        self.violations_by_lane.clear()
        self.violations_by_class.clear()

    def _record_violation(self, violation: RedLightViolation):
        self.violations.append(violation)
        self.violation_count = len(self.violations)
        self.violations_by_lane[violation.lane_name] += 1
        self.violations_by_class[violation.vehicle_class] += 1

    def _save_snapshot(self, frame, violation_id: str) -> str:
        path = self.snapshot_dir / f"{violation_id}.jpg"
        if frame is not None:
            cv2.imwrite(str(path), frame)
        return str(path)


def _iter_violations(violations: Iterable[RedLightViolation]):
    if hasattr(violations, "values"):
        return list(violations.values())
    return list(violations)


def _orientation(a, b, c):
    return (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])


def _segments_intersect(p1, q1, p2, q2):
    o1 = _orientation(p1, q1, p2)
    o2 = _orientation(p1, q1, q2)
    o3 = _orientation(p2, q2, p1)
    o4 = _orientation(p2, q2, q1)
    return (o1 == 0 or o2 == 0 or (o1 > 0) != (o2 > 0)) and (
        o3 == 0 or o4 == 0 or (o3 > 0) != (o4 > 0)
    )
