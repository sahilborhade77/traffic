"""
Anomaly Detection Module

Uses Isolation Forest to detect unusual traffic patterns like accidents,
sudden congestion, or unexpected vehicle behavior.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging
import pickle
import os

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)


class AnomalyType(Enum):
    """Types of traffic anomalies detected."""
    ACCIDENT = "accident"                    # Sudden stop/congestion
    CONGESTION_SPIKE = "congestion_spike"    # Rapid congestion increase
    SPEED_DROP = "speed_drop"                # Sudden speed decrease
    DENSITY_SPIKE = "density_spike"          # Vehicle count surge
    STOP_AND_GO = "stop_and_go"              # Erratic speed patterns
    UNUSUAL_PATTERN = "unusual_pattern"      # General anomaly
    QUEUE_BUILDUP = "queue_buildup"          # Rapid queue formation


class AnomalySeverity(Enum):
    """Severity levels for anomalies."""
    LOW = 1        # Minor deviation
    MEDIUM = 2     # Significant anomaly
    HIGH = 3       # Critical event
    CRITICAL = 4   # System-level alert


@dataclass
class TrafficSnapshot:
    """Point-in-time traffic snapshot."""
    timestamp: datetime
    lane: str
    vehicle_count: int
    vehicle_density: float
    average_speed: float
    max_speed: float
    queue_length: float
    wait_time: float
    speed_variance: float  # Variance in vehicle speeds
    queue_growth_rate: float  # (m/min)
    congestion_level: str  # low, medium, high
    
    def to_features(self) -> np.ndarray:
        """Convert to feature array."""
        return np.array([
            self.vehicle_count,
            self.vehicle_density,
            self.average_speed,
            self.max_speed,
            self.queue_length,
            self.wait_time,
            self.speed_variance,
            self.queue_growth_rate
        ]).reshape(1, -1)


@dataclass
class AnomalyAlert:
    """Detected anomaly alert."""
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    lane: str
    timestamp: datetime
    anomaly_score: float              # 0-1, higher = more anomalous
    deviation_details: Dict
    recommended_action: str
    confidence: float = 0.0            # 0-1
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'anomaly_type': self.anomaly_type.value,
            'severity': self.severity.name,
            'lane': self.lane,
            'timestamp': self.timestamp.isoformat(),
            'anomaly_score': float(self.anomaly_score),
            'deviation_details': self.deviation_details,
            'recommended_action': self.recommended_action,
            'confidence': float(self.confidence)
        }


class AnomalyDetector:
    """
    Isolation Forest-based anomaly detection for traffic.
    
    Features monitored:
    - Vehicle count (sudden increases)
    - Vehicle density (saturation)
    - Average speed (drops)
    - Speed variance (stop-and-go patterns)
    - Queue length and growth rate
    - Wait time spikes
    """
    
    FEATURE_NAMES = [
        'vehicle_count', 'vehicle_density', 'average_speed',
        'max_speed', 'queue_length', 'wait_time',
        'speed_variance', 'queue_growth_rate'
    ]
    
    def __init__(
        self,
        contamination: float = 0.1,  # Expected % of anomalies
        random_state: int = 42,
        model_path: Optional[str] = None
    ):
        """
        Initialize anomaly detector.
        
        Args:
            contamination: Expected proportion of anomalies (0-1)
            random_state: Random seed
            model_path: Path to load pretrained model
        """
        self.contamination = contamination
        self.random_state = random_state
        self.model_path = model_path
        
        # Initialize Isolation Forest
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=100,
            max_samples='auto',
            n_jobs=-1
        )
        
        # Feature scaling
        self.scaler = StandardScaler()
        
        # Baseline statistics (for threshold calculation)
        self.baseline_stats: Dict[str, Dict] = {}
        
        # History for context
        self.snapshot_history: Dict[str, list] = {}  # lane -> deque of snapshots
        self.anomaly_history: List[AnomalyAlert] = []
        
        self.is_trained = False
        self.training_timestamp: Optional[datetime] = None
        
        # Load model if provided
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)
        
        logger.info(f"AnomalyDetector initialized (contamination={contamination})")
    
    def train(
        self,
        snapshots_df: pd.DataFrame,
        verbose: bool = True
    ) -> Dict:
        """
        Train the Isolation Forest model.
        
        Args:
            snapshots_df: DataFrame with traffic snapshots
            verbose: Print training info
            
        Returns:
            Training results
        """
        # Validate features
        assert set(self.FEATURE_NAMES).issubset(set(snapshots_df.columns)), \
            f"Missing required features. Need: {self.FEATURE_NAMES}"
        
        # Extract features
        X = snapshots_df[self.FEATURE_NAMES].values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        logger.info(f"Training Isolation Forest on {len(X)} samples...")
        self.model.fit(X_scaled)
        
        # Calculate baseline statistics per lane (if lane column exists)
        if 'lane' in snapshots_df.columns:
            for lane in snapshots_df['lane'].unique():
                lane_data = snapshots_df[snapshots_df['lane'] == lane][self.FEATURE_NAMES]
                self.baseline_stats[lane] = {
                    'mean': lane_data.mean().to_dict(),
                    'std': lane_data.std().to_dict(),
                    'min': lane_data.min().to_dict(),
                    'max': lane_data.max().to_dict()
                }
        
        # Calculate global baseline
        self.baseline_stats['global'] = {
            'mean': snapshots_df[self.FEATURE_NAMES].mean().to_dict(),
            'std': snapshots_df[self.FEATURE_NAMES].std().to_dict(),
            'min': snapshots_df[self.FEATURE_NAMES].min().to_dict(),
            'max': snapshots_df[self.FEATURE_NAMES].max().to_dict()
        }
        
        self.is_trained = True
        self.training_timestamp = datetime.now()
        
        # Calculate anomaly stats
        predictions = self.model.predict(X_scaled)
        n_anomalies = (predictions == -1).sum()
        
        results = {
            'n_samples': len(X),
            'n_anomalies_found': int(n_anomalies),
            'anomaly_rate': float(n_anomalies / len(X)),
            'contamination_param': self.contamination,
            'n_features': len(self.FEATURE_NAMES),
            'baseline_stats': self.baseline_stats
        }
        
        if verbose:
            logger.info(f"Training complete:")
            logger.info(f"  Samples: {len(X)}")
            logger.info(f"  Anomalies found: {n_anomalies} ({n_anomalies/len(X)*100:.1f}%)")
            logger.info(f"  Baseline stats calculated for {len(self.baseline_stats)} lanes")
        
        return results
    
    def detect(
        self,
        snapshot: Union[TrafficSnapshot, Dict, np.ndarray]
    ) -> Tuple[bool, float]:
        """
        Detect if a snapshot is anomalous.
        
        Args:
            snapshot: Traffic snapshot
            
        Returns:
            (is_anomaly, anomaly_score) tuple
        """
        assert self.is_trained, "Model must be trained first. Call train() method."
        
        # Convert to array
        if isinstance(snapshot, TrafficSnapshot):
            X = snapshot.to_features()
        elif isinstance(snapshot, dict):
            X = np.array([snapshot.get(f, 0) for f in self.FEATURE_NAMES]).reshape(1, -1)
        else:
            X = np.array(snapshot).reshape(1, -1)
        
        # Scale
        X_scaled = self.scaler.transform(X)
        
        # Get prediction (-1 for anomaly, 1 for normal)
        prediction = self.model.predict(X_scaled)[0]
        
        # Get anomaly score (negative values)
        anomaly_score = -self.model.score_samples(X_scaled)[0]
        
        is_anomaly = prediction == -1
        
        return is_anomaly, float(anomaly_score)
    
    def detect_and_classify(
        self,
        snapshot: TrafficSnapshot
    ) -> Optional[AnomalyAlert]:
        """
        Detect anomaly and classify its type.
        
        Args:
            snapshot: Traffic snapshot
            
        Returns:
            AnomalyAlert if anomaly detected, None otherwise
        """
        is_anomaly, anomaly_score = self.detect(snapshot)
        
        if not is_anomaly:
            return None
        
        # Get baseline for comparison
        baseline = self.baseline_stats.get(
            snapshot.lane,
            self.baseline_stats.get('global')
        )
        
        if not baseline:
            # No baseline, generic anomaly
            return AnomalyAlert(
                anomaly_type=AnomalyType.UNUSUAL_PATTERN,
                severity=self._score_to_severity(anomaly_score),
                lane=snapshot.lane,
                timestamp=snapshot.timestamp,
                anomaly_score=anomaly_score,
                deviation_details={},
                recommended_action="Investigate traffic conditions",
                confidence=anomaly_score
            )
        
        # Classify anomaly type based on deviation patterns
        anomaly_type, details = self._classify_anomaly(snapshot, baseline)
        severity = self._score_to_severity(anomaly_score)
        action = self._recommend_action(anomaly_type, severity)
        
        alert = AnomalyAlert(
            anomaly_type=anomaly_type,
            severity=severity,
            lane=snapshot.lane,
            timestamp=snapshot.timestamp,
            anomaly_score=anomaly_score,
            deviation_details=details,
            recommended_action=action,
            confidence=anomaly_score
        )
        
        # Store in history
        self.anomaly_history.append(alert)
        
        return alert
    
    def _classify_anomaly(
        self,
        snapshot: TrafficSnapshot,
        baseline: Dict
    ) -> Tuple[AnomalyType, Dict]:
        """
        Classify the type of anomaly.
        
        Args:
            snapshot: Current snapshot
            baseline: Baseline statistics
            
        Returns:
            (anomaly_type, details) tuple
        """
        base_mean = baseline['mean']
        base_std = baseline['std']
        
        details = {}
        
        # Speed drop (potential accident)
        speed_deviation = (snapshot.average_speed - base_mean['average_speed']) / (base_std['average_speed'] + 1e-6)
        if speed_deviation < -1.5:
            details['speed_drop'] = abs(speed_deviation)
            return AnomalyType.SPEED_DROP, details
        
        # Density spike
        density_deviation = (snapshot.vehicle_density - base_mean['vehicle_density']) / (base_std['vehicle_density'] + 1e-6)
        if density_deviation > 2.0:
            details['density_spike'] = density_deviation
            return AnomalyType.DENSITY_SPIKE, details
        
        # Queue buildup
        queue_deviation = (snapshot.queue_length - base_mean['queue_length']) / (base_std['queue_length'] + 1e-6)
        if queue_deviation > 2.0:
            details['queue_buildup'] = queue_deviation
            return AnomalyType.QUEUE_BUILDUP, details
        
        # Stop-and-go (high speed variance)
        variance_deviation = (snapshot.speed_variance - base_mean['speed_variance']) / (base_std['speed_variance'] + 1e-6)
        if variance_deviation > 1.5:
            details['stop_and_go'] = variance_deviation
            return AnomalyType.STOP_AND_GO, details
        
        # Congestion spike
        wait_deviation = (snapshot.wait_time - base_mean['wait_time']) / (base_std['wait_time'] + 1e-6)
        if wait_deviation > 1.5:
            details['congestion_spike'] = wait_deviation
            return AnomalyType.CONGESTION_SPIKE, details
        
        # Generic unusual pattern
        details['multiple_deviations'] = {
            'speed': float(speed_deviation),
            'density': float(density_deviation),
            'queue': float(queue_deviation),
            'variance': float(variance_deviation),
            'wait_time': float(wait_deviation)
        }
        return AnomalyType.UNUSUAL_PATTERN, details
    
    def _score_to_severity(self, anomaly_score: float) -> AnomalySeverity:
        """Convert anomaly score to severity level."""
        if anomaly_score < 0.3:
            return AnomalySeverity.LOW
        elif anomaly_score < 0.6:
            return AnomalySeverity.MEDIUM
        elif anomaly_score < 0.85:
            return AnomalySeverity.HIGH
        else:
            return AnomalySeverity.CRITICAL
    
    def _recommend_action(
        self,
        anomaly_type: AnomalyType,
        severity: AnomalySeverity
    ) -> str:
        """Generate recommended action based on anomaly."""
        base_actions = {
            AnomalyType.ACCIDENT: "Check for accidents; dispatch traffic management",
            AnomalyType.CONGESTION_SPIKE: "Increase signal duration; activate adaptive control",
            AnomalyType.SPEED_DROP: "Alert drivers; check for obstacles or incidents",
            AnomalyType.DENSITY_SPIKE: "Redirect traffic; activate alternate routes",
            AnomalyType.STOP_AND_GO: "Optimize signal timing; improve lane management",
            AnomalyType.QUEUE_BUILDUP: "Address upstream congestion; check for bottlenecks",
            AnomalyType.UNUSUAL_PATTERN: "Monitor situation; conduct manual inspection"
        }
        
        action = base_actions.get(anomaly_type, "Investigate traffic conditions")
        
        if severity == AnomalySeverity.CRITICAL:
            action = f"URGENT: {action} - Activate emergency protocols"
        
        return action
    
    def detect_batch(
        self,
        snapshots_list: List[Union[TrafficSnapshot, Dict]]
    ) -> List[Optional[AnomalyAlert]]:
        """
        Detect anomalies in batch.
        
        Args:
            snapshots_list: List of snapshots
            
        Returns:
            List of AnomalyAlerts (None for normal observations)
        """
        alerts = []
        for snapshot in snapshots_list:
            if isinstance(snapshot, dict):
                snapshot = TrafficSnapshot(**snapshot)
            alert = self.detect_and_classify(snapshot)
            alerts.append(alert)
        
        return alerts
    
    def get_anomaly_statistics(self) -> Dict:
        """Get statistics about detected anomalies."""
        if not self.anomaly_history:
            return {
                'total_anomalies': 0,
                'by_type': {},
                'by_severity': {},
                'by_lane': {}
            }
        
        anomalies = self.anomaly_history
        
        # Count by type
        by_type = {}
        for alert in anomalies:
            type_name = alert.anomaly_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
        
        # Count by severity
        by_severity = {}
        for alert in anomalies:
            sev_name = alert.severity.name
            by_severity[sev_name] = by_severity.get(sev_name, 0) + 1
        
        # Count by lane
        by_lane = {}
        for alert in anomalies:
            lane = alert.lane
            by_lane[lane] = by_lane.get(lane, 0) + 1
        
        # Average severity
        avg_score = np.mean([a.anomaly_score for a in anomalies])
        
        return {
            'total_anomalies': len(anomalies),
            'by_type': by_type,
            'by_severity': by_severity,
            'by_lane': by_lane,
            'average_anomaly_score': float(avg_score),
            'latest_anomaly': anomalies[-1].to_dict() if anomalies else None
        }
    
    def get_recent_anomalies(self, minutes: int = 60) -> List[AnomalyAlert]:
        """Get anomalies from recent time period."""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [
            a for a in self.anomaly_history
            if a.timestamp >= cutoff_time
        ]
    
    def save_model(self, path: str) -> None:
        """Save trained model to disk."""
        assert self.is_trained, "Model must be trained before saving"
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'baseline_stats': self.baseline_stats,
            'training_timestamp': self.training_timestamp,
            'feature_names': self.FEATURE_NAMES
        }
        
        with open(path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Anomaly detector saved to {path}")
    
    def load_model(self, path: str) -> None:
        """Load trained model from disk."""
        with open(path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.baseline_stats = model_data['baseline_stats']
        self.training_timestamp = model_data['training_timestamp']
        
        self.is_trained = True
        logger.info(f"Anomaly detector loaded from {path}")
    
    def reset_history(self) -> None:
        """Clear anomaly history."""
        self.anomaly_history.clear()
        logger.info("Anomaly history cleared")
