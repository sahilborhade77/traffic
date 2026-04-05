"""
Congestion Prediction Module

Uses Random Forest classifier to predict congestion levels (low/medium/high)
based on temporal features (time, day), weather, and traffic metrics.
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

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

logger = logging.getLogger(__name__)


class CongestionLevel(Enum):
    """Congestion severity levels."""
    LOW = "low"          # Free flowing, <30% capacity
    MEDIUM = "medium"    # Moderate traffic, 30-70% capacity
    HIGH = "high"        # Heavy congestion, >70% capacity


@dataclass
class CongestionFeatures:
    """Features for congestion prediction."""
    # Temporal features
    hour_of_day: int          # 0-23
    day_of_week: int          # 0-6 (Monday=0)
    is_weekend: int           # 0 or 1
    is_holiday: int           # 0 or 1
    
    # Traffic metrics
    vehicle_count: float      # Current vehicles
    vehicle_density: float    # Vehicles per lane area
    average_speed: float      # km/h
    queue_length: float       # meters
    wait_time: float          # seconds
    
    # Weather conditions (if available)
    precipitation: float      # mm
    visibility: float         # km
    temperature: float        # Celsius
    
    # Historical context
    prev_congestion_level: str = "medium"  # Previous hour
    avg_speed_trend: float = 0.0            # 1h average change
    vehicle_count_trend: float = 0.0        # 1h change
    
    def to_array(self) -> np.ndarray:
        """Convert to feature array for model."""
        return np.array([
            self.hour_of_day,
            self.day_of_week,
            self.is_weekend,
            self.is_holiday,
            self.vehicle_count,
            self.vehicle_density,
            self.average_speed,
            self.queue_length,
            self.wait_time,
            self.precipitation,
            self.visibility,
            self.temperature,
            self.avg_speed_trend,
            self.vehicle_count_trend
        ]).reshape(1, -1)
    
    @classmethod
    def from_metrics(
        cls,
        metrics: Dict,
        weather: Optional[Dict] = None,
        prev_level: str = "medium",
        trends: Optional[Dict] = None
    ) -> 'CongestionFeatures':
        """
        Create features from traffic metrics.
        
        Args:
            metrics: Traffic metrics dict
            weather: Weather data dict
            prev_level: Previous congestion level
            trends: Trend data (speed_change, count_change)
            
        Returns:
            CongestionFeatures instance
        """
        now = datetime.now()
        
        return cls(
            hour_of_day=now.hour,
            day_of_week=now.weekday(),
            is_weekend=1 if now.weekday() >= 5 else 0,
            is_holiday=0,  # Would need holiday calendar
            
            vehicle_count=metrics.get('vehicle_count', 0),
            vehicle_density=metrics.get('density', 0.0),
            average_speed=metrics.get('average_speed', 30.0),
            queue_length=metrics.get('queue_length', 0.0),
            wait_time=metrics.get('wait_time', 0.0),
            
            precipitation=weather.get('precipitation', 0) if weather else 0,
            visibility=weather.get('visibility', 10) if weather else 10,
            temperature=weather.get('temperature', 25) if weather else 25,
            
            prev_congestion_level=prev_level,
            avg_speed_trend=trends.get('speed_change', 0) if trends else 0,
            vehicle_count_trend=trends.get('count_change', 0) if trends else 0
        )


@dataclass
class CongestionPrediction:
    """Prediction result."""
    predicted_level: CongestionLevel
    confidence: float                    # 0-1
    probabilities: Dict[str, float]      # Probabilities for each class
    timestamp: datetime = field(default_factory=datetime.now)
    lane: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'predicted_level': self.predicted_level.value,
            'confidence': float(self.confidence),
            'probabilities': {
                'low': float(self.probabilities.get('low', 0)),
                'medium': float(self.probabilities.get('medium', 0)),
                'high': float(self.probabilities.get('high', 0))
            },
            'timestamp': self.timestamp.isoformat(),
            'lane': self.lane
        }


class CongestionPredictor:
    """
    Random Forest-based congestion level predictor.
    
    Features used:
    - Temporal: hour, day of week, weekend, holiday
    - Traffic: vehicle count, density, speed, queue length, wait time
    - Weather: precipitation, visibility, temperature
    - Trends: speed and count changes from previous hour
    """
    
    FEATURE_NAMES = [
        'hour_of_day', 'day_of_week', 'is_weekend', 'is_holiday',
        'vehicle_count', 'vehicle_density', 'average_speed',
        'queue_length', 'wait_time',
        'precipitation', 'visibility', 'temperature',
        'avg_speed_trend', 'vehicle_count_trend'
    ]
    
    TARGET_CLASSES = ['low', 'medium', 'high']
    
    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 15,
        min_samples_split: int = 10,
        min_samples_leaf: int = 5,
        model_path: Optional[str] = None
    ):
        """
        Initialize congestion predictor.
        
        Args:
            n_estimators: Number of trees
            max_depth: Max tree depth
            min_samples_split: Min samples to split node
            min_samples_leaf: Min samples in leaf node
            model_path: Path to load pretrained model
        """
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.model_path = model_path
        
        # Initialize model
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            min_samples_leaf=min_samples_leaf,
            n_jobs=-1,
            random_state=42
        )
        
        # Feature scaling
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        
        self.is_trained = False
        self.training_history: List[Dict] = []
        
        # Load model if provided
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)
        
        logger.info("CongestionPredictor initialized")
    
    def train(
        self,
        features_df: pd.DataFrame,
        labels: Union[List[str], np.ndarray],
        test_size: float = 0.2,
        verbose: bool = True
    ) -> Dict:
        """
        Train the Random Forest model.
        
        Args:
            features_df: DataFrame with feature columns
            labels: List of congestion levels ('low', 'medium', 'high')
            test_size: Train/test split ratio
            verbose: Print metrics
            
        Returns:
            Training results dictionary
        """
        # Validate features
        assert set(self.FEATURE_NAMES).issubset(set(features_df.columns)), \
            f"Missing required features. Need: {self.FEATURE_NAMES}"
        
        # Extract features
        X = features_df[self.FEATURE_NAMES].values
        
        # Ensure labels are strings
        labels = [str(l).lower() for l in labels]
        
        # Encode labels
        y = self.label_encoder.fit_transform(labels)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Train model
        logger.info(f"Training on {len(X_train)} samples...")
        self.model.fit(X_train, y_train)
        
        # Evaluate
        train_accuracy = self.model.score(X_train, y_train)
        test_accuracy = self.model.score(X_test, y_test)
        
        # Predictions for detailed metrics
        y_pred = self.model.predict(X_test)
        
        # Feature importance
        feature_importance = dict(zip(
            self.FEATURE_NAMES,
            self.model.feature_importances_
        ))
        
        results = {
            'train_accuracy': float(train_accuracy),
            'test_accuracy': float(test_accuracy),
            'n_samples': len(X),
            'feature_importance': feature_importance,
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
            'classification_report': classification_report(
                y_test, y_pred,
                target_names=self.TARGET_CLASSES,
                output_dict=True
            )
        }
        
        # Store results
        self.training_history.append({
            'timestamp': datetime.now().isoformat(),
            'results': results
        })
        
        self.is_trained = True
        
        if verbose:
            logger.info(f"Training complete:")
            logger.info(f"  Train accuracy: {train_accuracy:.3f}")
            logger.info(f"  Test accuracy: {test_accuracy:.3f}")
            logger.info(f"  Top features: {sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:3]}")
        
        return results
    
    def predict(
        self,
        features: Union[CongestionFeatures, np.ndarray, pd.DataFrame]
    ) -> CongestionPrediction:
        """
        Predict congestion level.
        
        Args:
            features: CongestionFeatures instance, numpy array, or DataFrame row
            
        Returns:
            CongestionPrediction object
        """
        assert self.is_trained, "Model must be trained first. Call train() method."
        
        # Convert to array
        if isinstance(features, CongestionFeatures):
            X = features.to_array()
        elif isinstance(features, pd.DataFrame):
            X = features[self.FEATURE_NAMES].values
        else:
            X = np.array(features).reshape(1, -1)
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Get prediction and probabilities
        prediction = self.model.predict(X_scaled)[0]
        probabilities = self.model.predict_proba(X_scaled)[0]
        
        # Decode label
        predicted_level = self.label_encoder.inverse_transform([prediction])[0]
        
        # Get confidence (max probability)
        confidence = float(np.max(probabilities))
        
        # Create probability dict
        prob_dict = {
            self.label_encoder.inverse_transform([i])[0]: float(probabilities[i])
            for i in range(len(self.TARGET_CLASSES))
        }
        
        return CongestionPrediction(
            predicted_level=CongestionLevel(predicted_level.lower()),
            confidence=confidence,
            probabilities=prob_dict
        )
    
    def predict_batch(
        self,
        features_list: List[Union[CongestionFeatures, Dict]]
    ) -> List[CongestionPrediction]:
        """
        Predict multiple samples.
        
        Args:
            features_list: List of features
            
        Returns:
            List of predictions
        """
        predictions = []
        for features in features_list:
            if isinstance(features, dict):
                features = CongestionFeatures(**features)
            pred = self.predict(features)
            predictions.append(pred)
        
        return predictions
    
    def predict_for_lane(
        self,
        lane_name: str,
        metrics: Dict,
        weather: Optional[Dict] = None
    ) -> CongestionPrediction:
        """
        Predict congestion for a specific lane.
        
        Args:
            lane_name: Lane identifier
            metrics: Traffic metrics
            weather: Weather data
            
        Returns:
            CongestionPrediction with lane info
        """
        features = CongestionFeatures.from_metrics(metrics, weather)
        prediction = self.predict(features)
        prediction.lane = lane_name
        
        return prediction
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores."""
        assert self.is_trained, "Model must be trained first"
        return dict(zip(self.FEATURE_NAMES, self.model.feature_importances_))
    
    def analyze_features(self, feature_importance: Optional[Dict] = None) -> Dict:
        """
        Analyze which features are most important for predictions.
        
        Args:
            feature_importance: Custom importance dict (uses model if None)
            
        Returns:
            Analysis dictionary
        """
        if feature_importance is None:
            feature_importance = self.get_feature_importance()
        
        sorted_features = sorted(
            feature_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            'top_features': [name for name, _ in sorted_features[:3]],
            'feature_importance': dict(sorted_features),
            'temporal_importance': sum(
                score for name, score in sorted_features
                if any(x in name for x in ['hour', 'day', 'weekend'])
            ),
            'traffic_importance': sum(
                score for name, score in sorted_features
                if any(x in name for x in ['vehicle', 'speed', 'queue', 'wait'])
            ),
            'weather_importance': sum(
                score for name, score in sorted_features
                if any(x in name for x in ['precipitation', 'visibility', 'temperature'])
            )
        }
    
    def save_model(self, path: str) -> None:
        """Save trained model to disk."""
        assert self.is_trained, "Model must be trained before saving"
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'label_encoder': self.label_encoder,
            'feature_names': self.FEATURE_NAMES,
            'training_history': self.training_history
        }
        
        with open(path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str) -> None:
        """Load trained model from disk."""
        with open(path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.label_encoder = model_data['label_encoder']
        self.training_history = model_data.get('training_history', [])
        
        self.is_trained = True
        logger.info(f"Model loaded from {path}")
    
    def generate_training_report(self) -> Dict:
        """Generate comprehensive training report."""
        if not self.training_history:
            return {}
        
        latest = self.training_history[-1]['results']
        analysis = self.analyze_features(latest['feature_importance'])
        
        return {
            'timestamp': self.training_history[-1]['timestamp'],
            'model_accuracy': latest['test_accuracy'],
            'training_samples': latest['n_samples'],
            'feature_analysis': analysis,
            'class_metrics': latest['classification_report']
        }
