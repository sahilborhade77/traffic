"""Compatibility wrapper for legacy vision tracking imports."""

from src.tracking.deepsort_tracker import DeepSORTTracker, TrajectoryAnalyzer, VehicleTrack

__all__ = ["DeepSORTTracker", "TrajectoryAnalyzer", "VehicleTrack"]
