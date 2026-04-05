"""
Phase 8 Advanced ML Features - Integration & Usage Guide

Demonstrates usage of:
1. Vehicle Classification (Step 25)
2. Congestion Prediction (Step 26)
3. Anomaly Detection (Step 27)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the new modules
from src.prediction.vehicle_classifier import VehicleClassifier, LaneClassificationStats
from src.prediction.congestion_predictor import (
    CongestionPredictor, CongestionFeatures, CongestionLevel
)
from src.prediction.anomaly_detector import (
    AnomalyDetector, TrafficSnapshot, AnomalyType, AnomalySeverity
)


class Phase8Demonstrator:
    """Demonstrates Phase 8 ML features integration."""
    
    def __init__(self):
        """Initialize all Phase 8 components."""
        # Step 25: Vehicle Classification
        self.classifier = VehicleClassifier(history_window=300)
        
        # Step 26: Congestion Prediction
        self.congestion_predictor = CongestionPredictor(
            n_estimators=100,
            max_depth=15
        )
        
        # Step 27: Anomaly Detection
        self.anomaly_detector = AnomalyDetector(contamination=0.1)
        
        logger.info("Phase 8 Demonstrator initialized")
    
    # ========== STEP 25: Vehicle Classification ==========
    
    def demo_vehicle_classification(self):
        """Demonstrate vehicle classification capabilities."""
        logger.info("\n" + "="*60)
        logger.info("STEP 25: Vehicle Classification Demo")
        logger.info("="*60)
        
        # Simulate detection data
        detections = [
            {
                'track_id': 1, 'class_id': 2, 'confidence': 0.95,
                'speed': 45, 'bbox': (100, 100, 150, 150)
            },  # Car
            {
                'track_id': 2, 'class_id': 3, 'confidence': 0.92,
                'speed': 60, 'bbox': (200, 100, 220, 130)
            },  # Motorcycle
            {
                'track_id': 3, 'class_id': 5, 'confidence': 0.98,
                'speed': 30, 'bbox': (50, 200, 150, 280)
            },  # Bus
            {
                'track_id': 4, 'class_id': 7, 'confidence': 0.96,
                'speed': 40, 'bbox': (300, 150, 380, 250)
            },  # Truck
            {
                'track_id': 5, 'class_id': 2, 'confidence': 0.94,
                'speed': 50, 'bbox': (400, 100, 450, 150)
            },  # Car
        ]
        
        # Update classifier with detections
        timestamp = datetime.now().timestamp()
        for detection in detections:
            self.classifier.update_vehicle(
                track_id=detection['track_id'],
                detection=detection,
                lane_name='North',
                timestamp=timestamp
            )
        
        # Get classification statistics
        logger.info("\n--- Vehicle Classification Statistics ---")
        
        counts = self.classifier.get_class_counts()
        logger.info(f"Current vehicle counts: {counts}")
        
        distribution = self.classifier.get_class_distribution()
        logger.info(f"Distribution: {distribution}")
        
        stats = self.classifier.get_class_statistics()
        logger.info("\nDetailed statistics:")
        for class_name, data in stats.items():
            logger.info(f"  {class_name.upper()}:")
            logger.info(f"    Current: {data['current_count']} | Total: {data['total_count']}")
            logger.info(f"    Avg Speed: {data['average_speed']:.1f} km/h")
            logger.info(f"    Percentage: {data['percentage']:.1f}%")
        
        # Lane-specific stats
        lane_stats = self.classifier.get_lane_classification_stats('North', timestamp)
        logger.info(f"\nLane 'North' stats at {lane_stats.timestamp}:")
        logger.info(f"  Total vehicles: {lane_stats.total_vehicles}")
        logger.info(f"  Dominant class: {lane_stats.dominant_class}")
        logger.info(f"  Class distribution: {lane_stats.density_by_class}")
        
        # Detect anomalies in class distribution
        anomalies = self.classifier.detect_vehicle_type_anomalies('North')
        if anomalies:
            logger.info(f"\nDetected class distribution anomalies:")
            for anomaly in anomalies:
                logger.info(f"  {anomaly['class_name']}: {anomaly['deviation']:.2f} deviation")
        
        return stats
    
    # ========== STEP 26: Congestion Prediction ==========
    
    def demo_congestion_prediction(self):
        """Demonstrate congestion prediction."""
        logger.info("\n" + "="*60)
        logger.info("STEP 26: Congestion Prediction Demo")
        logger.info("="*60)
        
        # Generate synthetic training data
        logger.info("\n--- Generating training data ---")
        n_samples = 500
        
        hours = np.random.randint(0, 24, n_samples)
        days = np.random.randint(0, 7, n_samples)
        vehicle_counts = np.random.randint(5, 100, n_samples)
        speeds = np.random.uniform(10, 60, n_samples)
        queue_lengths = np.random.uniform(0, 200, n_samples)
        wait_times = np.random.uniform(0, 120, n_samples)
        
        # Create labels based on conditions
        labels = []
        for i in range(n_samples):
            if vehicle_counts[i] > 80 or speeds[i] < 20:
                labels.append('high')
            elif vehicle_counts[i] > 50 or speeds[i] < 30:
                labels.append('medium')
            else:
                labels.append('low')
        
        # Create training dataframe
        training_data = pd.DataFrame({
            'hour_of_day': hours,
            'day_of_week': days,
            'is_weekend': (days >= 5).astype(int),
            'is_holiday': np.zeros(n_samples, dtype=int),
            'vehicle_count': vehicle_counts,
            'vehicle_density': vehicle_counts / 100.0,
            'average_speed': speeds,
            'queue_length': queue_lengths,
            'wait_time': wait_times,
            'precipitation': np.random.uniform(0, 5, n_samples),
            'visibility': np.random.uniform(5, 20, n_samples),
            'temperature': np.random.uniform(10, 40, n_samples),
            'avg_speed_trend': np.random.uniform(-5, 5, n_samples),
            'vehicle_count_trend': np.random.uniform(-10, 10, n_samples)
        })
        
        logger.info(f"Training set size: {len(training_data)}")
        logger.info(f"Class distribution: {pd.Series(labels).value_counts().to_dict()}")
        
        # Train model
        logger.info("\n--- Training congestion predictor ---")
        results = self.congestion_predictor.train(training_data, labels, verbose=True)
        
        # Show feature importance
        logger.info("\n--- Feature Importance ---")
        importance = self.congestion_predictor.get_feature_importance()
        sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)
        for feature, score in sorted_features[:5]:
            logger.info(f"  {feature}: {score:.4f}")
        
        # Make predictions
        logger.info("\n--- Making predictions ---")
        test_features = CongestionFeatures(
            hour_of_day=18,           # Rush hour
            day_of_week=4,            # Friday
            is_weekend=0,
            is_holiday=0,
            vehicle_count=85,
            vehicle_density=0.85,
            average_speed=25,
            queue_length=150,
            wait_time=90,
            precipitation=0,
            visibility=15,
            temperature=28,
            avg_speed_trend=-2,
            vehicle_count_trend=10
        )
        
        prediction = self.congestion_predictor.predict(test_features)
        logger.info(f"Predicted congestion level: {prediction.predicted_level.value}")
        logger.info(f"Confidence: {prediction.confidence:.2%}")
        logger.info(f"Probabilities: {prediction.probabilities}")
        
        # Analyze features
        analysis = self.congestion_predictor.analyze_features(importance)
        logger.info(f"\nFeature category importance:")
        logger.info(f"  Temporal: {analysis['temporal_importance']:.2%}")
        logger.info(f"  Traffic: {analysis['traffic_importance']:.2%}")
        logger.info(f"  Weather: {analysis['weather_importance']:.2%}")
        
        return prediction
    
    # ========== STEP 27: Anomaly Detection ==========
    
    def demo_anomaly_detection(self):
        """Demonstrate anomaly detection."""
        logger.info("\n" + "="*60)
        logger.info("STEP 27: Anomaly Detection Demo")
        logger.info("="*60)
        
        # Generate synthetic baseline data
        logger.info("\n--- Generating baseline traffic data ---")
        n_samples = 300
        
        # Normal traffic pattern
        vehicle_counts = np.random.normal(40, 10, n_samples)
        vehicle_counts = np.clip(vehicle_counts, 5, 100)
        
        speeds = np.random.normal(35, 8, n_samples)
        speeds = np.clip(speeds, 10, 60)
        
        queue_lengths = np.random.normal(50, 20, n_samples)
        queue_lengths = np.clip(queue_lengths, 0, 200)
        
        wait_times = np.random.normal(45, 15, n_samples)
        wait_times = np.clip(wait_times, 0, 120)
        
        # Create training data
        training_data = pd.DataFrame({
            'vehicle_count': vehicle_counts,
            'vehicle_density': vehicle_counts / 100.0,
            'average_speed': speeds,
            'max_speed': speeds + np.random.uniform(5, 15, n_samples),
            'queue_length': queue_lengths,
            'wait_time': wait_times,
            'speed_variance': np.random.uniform(2, 15, n_samples),
            'queue_growth_rate': np.random.normal(0, 5, n_samples),
            'lane': ['North'] * n_samples
        })
        
        logger.info(f"Baseline data size: {len(training_data)}")
        
        # Train anomaly detector
        logger.info("\n--- Training anomaly detector ---")
        train_results = self.anomaly_detector.train(training_data, verbose=True)
        
        # Create test snapshots (including anomalies)
        logger.info("\n--- Testing anomaly detection ---")
        
        # Normal snapshot
        normal_snapshot = TrafficSnapshot(
            timestamp=datetime.now(),
            lane='North',
            vehicle_count=38,
            vehicle_density=0.38,
            average_speed=34,
            max_speed=48,
            queue_length=52,
            wait_time=42,
            speed_variance=8,
            queue_growth_rate=1,
            congestion_level='medium'
        )
        
        alert = self.anomaly_detector.detect_and_classify(normal_snapshot)
        logger.info(f"Normal traffic: {'ANOMALY' if alert else 'NORMAL'}")
        
        # Accident scenario (sudden speed drop)
        accident_snapshot = TrafficSnapshot(
            timestamp=datetime.now(),
            lane='North',
            vehicle_count=85,           # High density
            vehicle_density=0.85,
            average_speed=8,            # Sudden drop!
            max_speed=15,
            queue_length=180,           # Long queue
            wait_time=110,              # Long wait
            speed_variance=20,          # High variance
            queue_growth_rate=15,       # Rapid growth
            congestion_level='high'
        )
        
        alert = self.anomaly_detector.detect_and_classify(accident_snapshot)
        if alert:
            logger.info(f"\nAccident detected:")
            logger.info(f"  Type: {alert.anomaly_type.value}")
            logger.info(f"  Severity: {alert.severity.name}")
            logger.info(f"  Score: {alert.anomaly_score:.2f}")
            logger.info(f"  Action: {alert.recommended_action}")
        
        # Congestion spike
        congestion_snapshot = TrafficSnapshot(
            timestamp=datetime.now(),
            lane='North',
            vehicle_count=95,           # Very high
            vehicle_density=0.95,
            average_speed=22,           # Lower than normal
            max_speed=32,
            queue_length=190,
            wait_time=105,
            speed_variance=6,
            queue_growth_rate=8,
            congestion_level='high'
        )
        
        alert = self.anomaly_detector.detect_and_classify(congestion_snapshot)
        if alert:
            logger.info(f"\nCongestion spike detected:")
            logger.info(f"  Type: {alert.anomaly_type.value}")
            logger.info(f"  Severity: {alert.severity.name}")
            logger.info(f"  Action: {alert.recommended_action}")
        
        # Get statistics
        logger.info("\n--- Anomaly Statistics ---")
        stats = self.anomaly_detector.get_anomaly_statistics()
        logger.info(f"Total anomalies detected: {stats['total_anomalies']}")
        logger.info(f"By type: {stats['by_type']}")
        logger.info(f"By severity: {stats['by_severity']}")
    
    # ========== INTEGRATION DEMO ==========
    
    def demo_integrated_system(self):
        """Demonstrate all three modules working together."""
        logger.info("\n" + "="*60)
        logger.info("INTEGRATED SYSTEM DEMO")
        logger.info("="*60)
        
        logger.info("\nScenario: Friday 6 PM, Heavy traffic with accident")
        
        # Step 1: Classify vehicles detecton
        logger.info("\n1. Classiffying vehicles...")
        detections = [
            {'track_id': i, 'class_id': np.random.choice([2, 3, 5, 7]),
             'confidence': 0.9 + np.random.uniform(0, 0.1),
             'speed': np.random.uniform(15, 50), 'bbox': (0, 0, 50, 50)}
            for i in range(80)
        ]
        
        for detection in detections:
            self.classifier.update_vehicle(
                track_id=detection['track_id'],
                detection=detection,
                lane_name='North',
                timestamp=datetime.now().timestamp()
            )
        
        class_counts = self.classifier.get_class_counts()
        logger.info(f"Vehicle distribution: {class_counts}")
        
        # Step 2: Predict congestion
        logger.info("\n2. Predicting congestion...")
        avg_speed = np.mean([d['speed'] for d in detections])
        
        congestion_features = CongestionFeatures(
            hour_of_day=18,
            day_of_week=4,
            is_weekend=0,
            is_holiday=0,
            vehicle_count=len(detections),
            vehicle_density=len(detections) / 100,
            average_speed=avg_speed,
            queue_length=150,
            wait_time=85,
            precipitation=0,
            visibility=15,
            temperature=28
        )
        
        if self.congestion_predictor.is_trained:
            prediction = self.congestion_predictor.predict(congestion_features)
            logger.info(f"Predicted: {prediction.predicted_level.value} congestion")
            logger.info(f"Confidence: {prediction.confidence:.0%}")
        
        # Step 3: Detect anomalies
        logger.info("\n3. Detecting anomalies...")
        snapshot = TrafficSnapshot(
            timestamp=datetime.now(),
            lane='North',
            vehicle_count=len(detections),
            vehicle_density=len(detections) / 100,
            average_speed=15,  # Accident!
            max_speed=25,
            queue_length=160,
            wait_time=100,
            speed_variance=18,
            queue_growth_rate=10,
            congestion_level='high'
        )
        
        if self.anomaly_detector.is_trained:
            alert = self.anomaly_detector.detect_and_classify(snapshot)
            if alert:
                logger.info(f"ALERT: {alert.anomaly_type.value.upper()}")
                logger.info(f"Action: {alert.recommended_action}")
    
    def run_all_demos(self):
        """Run all demonstrations."""
        try:
            self.demo_vehicle_classification()
            self.demo_congestion_prediction()
            self.demo_anomaly_detection()
            self.demo_integrated_system()
            
            logger.info("\n" + "="*60)
            logger.info("All Phase 8 demos completed successfully!")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Error in demo: {e}", exc_info=True)


# ========== MAIN EXECUTION ==========

if __name__ == '__main__':
    demonstrator = Phase8Demonstrator()
    demonstrator.run_all_demos()
