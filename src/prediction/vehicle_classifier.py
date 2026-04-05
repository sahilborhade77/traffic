"""
Vehicle Classification Module

Classifies vehicles into categories (car, truck, bus, motorcycle, auto) 
using YOLO class IDs with separate counting and analytics per category.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class VehicleClassMetrics:
    """Metrics for each vehicle class."""
    class_name: str
    total_count: int = 0
    current_count: int = 0
    average_speed: float = 0.0
    average_confidence: float = 0.0
    total_time_in_scene: float = 0.0  # seconds
    peak_count: int = 0
    peak_time: Optional[str] = None


@dataclass
class LaneClassificationStats:
    """Per-lane classification statistics."""
    lane_name: str
    timestamp: datetime
    metrics: Dict[str, VehicleClassMetrics] = field(default_factory=dict)
    total_vehicles: int = 0
    density_by_class: Dict[str, float] = field(default_factory=dict)  # percentage
    dominant_class: Optional[str] = None


class VehicleClassifier:
    """
    Multi-class vehicle classification system using YOLO outputs.
    
    Vehicle Classes:
    - car: 2 (passenger vehicles, sedans, SUVs)
    - motorcycle: 3 (two-wheeled vehicles)
    - bus: 5 (large transport vehicles)
    - truck: 7 (cargo vehicles)
    - auto: 0 (auto-rickshaw, tuk-tuk)
    """
    
    # YOLO class ID to human-readable mapping
    YOLO_CLASS_MAP = {
        0: "auto",        # Auto-rickshaw/tuk-tuk
        2: "car",         # Passenger vehicle
        3: "motorcycle",  # Two-wheeler
        5: "bus",         # Public transport
        7: "truck"        # Commercial vehicle
    }
    
    # Reverse mapping
    CLASS_TO_YOLO_ID = {v: k for k, v in YOLO_CLASS_MAP.items()}
    
    def __init__(
        self,
        history_window: int = 300,  # 5 minutes
        speed_unit: str = "kmh"     # kmh or ms
    ):
        """
        Initialize vehicle classifier.
        
        Args:
            history_window: Seconds to maintain history
            speed_unit: Speed unit for calculations
        """
        self.history_window = history_window
        self.speed_unit = speed_unit
        
        # Track vehicle appearances
        self.vehicle_history: Dict[int, deque] = defaultdict(
            lambda: deque(maxlen=history_window)
        )
        
        # Per-class statistics
        self.class_stats: Dict[str, VehicleClassMetrics] = {
            class_name: VehicleClassMetrics(class_name=class_name)
            for class_name in self.YOLO_CLASS_MAP.values()
        }
        
        # Per-lane statistics
        self.lane_stats: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=int(history_window / 5))  # 5-second intervals
        )
        
        # Active tracks per class
        self.active_vehicles: Dict[str, set] = {
            class_name: set() for class_name in self.YOLO_CLASS_MAP.values()
        }
        
        logger.info("VehicleClassifier initialized with %d classes", len(self.YOLO_CLASS_MAP))
    
    def classify_detection(self, detection: Dict) -> Optional[str]:
        """
        Classify a single detection by YOLO class.
        
        Args:
            detection: Detection dict with 'class_id' key
            
        Returns:
            Class name or None if unmapped
        """
        class_id = detection.get('class_id')
        return self.YOLO_CLASS_MAP.get(class_id)
    
    def update_vehicle(
        self,
        track_id: int,
        detection: Dict,
        lane_name: str,
        timestamp: float
    ) -> None:
        """
        Update vehicle tracking data for classification.
        
        Args:
            track_id: Vehicle tracking ID
            detection: Detection with class_id, confidence, bbox
            lane_name: Current lane
            timestamp: Detection timestamp (unix)
        """
        class_name = self.classify_detection(detection)
        if not class_name:
            return
        
        # Record in history
        record = {
            'track_id': track_id,
            'class_name': class_name,
            'confidence': detection.get('confidence', 0.0),
            'speed': detection.get('speed', 0.0),
            'bbox': detection.get('bbox'),
            'lane': lane_name,
            'timestamp': timestamp
        }
        self.vehicle_history[track_id].append(record)
        
        # Update active vehicles
        if track_id not in self.active_vehicles[class_name]:
            self.active_vehicles[class_name].add(track_id)
            self.class_stats[class_name].total_count += 1
            logger.debug(f"New {class_name} detected: {track_id}")
    
    def get_class_counts(self, lane_name: Optional[str] = None) -> Dict[str, int]:
        """
        Get current vehicle counts per class.
        
        Args:
            lane_name: Optional lane filter
            
        Returns:
            Dict mapping class names to counts
        """
        if lane_name:
            # Count vehicles currently in specific lane
            counts = {class_name: 0 for class_name in self.YOLO_CLASS_MAP.values()}
            for class_name, track_ids in self.active_vehicles.items():
                for track_id in track_ids:
                    if self.vehicle_history[track_id]:
                        latest = self.vehicle_history[track_id][-1]
                        if latest['lane'] == lane_name:
                            counts[class_name] += 1
            return counts
        else:
            # Total active vehicles per class
            return {
                class_name: len(track_ids)
                for class_name, track_ids in self.active_vehicles.items()
            }
    
    def get_class_distribution(self, lane_name: Optional[str] = None) -> Dict[str, float]:
        """
        Get percentage distribution of vehicle classes.
        
        Args:
            lane_name: Optional lane filter
            
        Returns:
            Dict with class names and percentages (0-100)
        """
        counts = self.get_class_counts(lane_name)
        total = sum(counts.values())
        
        if total == 0:
            return {class_name: 0.0 for class_name in counts}
        
        return {class_name: (count / total) * 100 for class_name, count in counts.items()}
    
    def get_class_speeds(self, class_name: str) -> List[float]:
        """
        Get all recorded speeds for a vehicle class.
        
        Args:
            class_name: Vehicle class name
            
        Returns:
            List of speeds
        """
        speeds = []
        for track_id in self.active_vehicles[class_name]:
            if self.vehicle_history[track_id]:
                for record in self.vehicle_history[track_id]:
                    if record['class_name'] == class_name and record['speed'] > 0:
                        speeds.append(record['speed'])
        return speeds
    
    def get_class_statistics(self) -> Dict[str, Dict]:
        """
        Get comprehensive statistics for all classes.
        
        Returns:
            Dict with statistics per class
        """
        stats = {}
        counts = self.get_class_counts()
        distribution = self.get_class_distribution()
        
        for class_name in self.YOLO_CLASS_MAP.values():
            speeds = self.get_class_speeds(class_name)
            
            stats[class_name] = {
                'current_count': counts[class_name],
                'total_count': self.class_stats[class_name].total_count,
                'percentage': distribution[class_name],
                'average_speed': np.mean(speeds) if speeds else 0.0,
                'max_speed': np.max(speeds) if speeds else 0.0,
                'min_speed': np.min(speeds) if speeds else 0.0,
                'speed_std': np.std(speeds) if len(speeds) > 1 else 0.0,
                'sample_count': len(speeds)
            }
        
        return stats
    
    def get_lane_classification_stats(
        self,
        lane_name: str,
        timestamp: Optional[float] = None
    ) -> LaneClassificationStats:
        """
        Get classification statistics for a specific lane.
        
        Args:
            lane_name: Lane identifier
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            LaneClassificationStats object
        """
        if timestamp is None:
            timestamp = datetime.now().timestamp()
        
        counts = self.get_class_counts(lane_name)
        total = sum(counts.values())
        
        # Create metrics for each class
        metrics = {}
        for class_name, count in counts.items():
            speeds = self.get_class_speeds(class_name)
            metrics[class_name] = VehicleClassMetrics(
                class_name=class_name,
                current_count=count,
                total_count=self.class_stats[class_name].total_count,
                average_speed=np.mean(speeds) if speeds else 0.0,
                average_confidence=np.mean([
                    rec['confidence'] for rec in self.vehicle_history.values()
                    if rec and rec[-1]['class_name'] == class_name
                ]) if self.vehicle_history else 0.0
            )
        
        # Determine dominant class
        dominant_class = max(metrics.keys(), key=lambda k: metrics[k].current_count) if metrics else None
        
        return LaneClassificationStats(
            lane_name=lane_name,
            timestamp=datetime.fromtimestamp(timestamp),
            metrics=metrics,
            total_vehicles=total,
            density_by_class={
                cn: (counts[cn] / total * 100) if total > 0 else 0
                for cn in counts
            },
            dominant_class=dominant_class if total > 0 else None
        )
    
    def detect_vehicle_type_anomalies(self, lane_name: str, threshold: float = 2.0) -> List[Dict]:
        """
        Detect unusual class distributions (e.g., all trucks, no cars).
        
        Args:
            lane_name: Lane to analyze
            threshold: Standard deviations from mean (default 2.0)
            
        Returns:
            List of anomalies detected
        """
        distribution = self.get_class_distribution(lane_name)
        total = sum(self.get_class_counts(lane_name).values())
        
        if total < 5:
            return []
        
        # Expected distribution (uniform)
        expected_pct = 100 / len(self.YOLO_CLASS_MAP)
        std_dev = np.std(list(distribution.values()))
        
        anomalies = []
        for class_name, percentage in distribution.items():
            deviation = abs(percentage - expected_pct)
            if deviation > threshold * std_dev:
                anomalies.append({
                    'lane': lane_name,
                    'class_name': class_name,
                    'current_percentage': percentage,
                    'expected_percentage': expected_pct,
                    'deviation': deviation,
                    'severity': 'high' if deviation > 3 * std_dev else 'medium'
                })
        
        return anomalies
    
    def get_classification_summary(self) -> Dict:
        """
        Get summary of all classifications.
        
        Returns:
            Summary dictionary
        """
        all_counts = self.get_class_counts()
        all_stats = self.get_class_statistics()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_vehicles_tracked': sum(all_counts.values()),
            'total_unique_vehicles': sum(
                self.class_stats[cn].total_count 
                for cn in self.YOLO_CLASS_MAP.values()
            ),
            'vehicles_by_class': all_counts,
            'class_statistics': all_stats,
            'vehicles_by_class_percentage': self.get_class_distribution()
        }
    
    def reset(self) -> None:
        """Reset all statistics."""
        for class_name in self.class_stats:
            self.class_stats[class_name] = VehicleClassMetrics(class_name=class_name)
            self.active_vehicles[class_name].clear()
        self.vehicle_history.clear()
        self.lane_stats.clear()
        logger.info("VehicleClassifier reset")
