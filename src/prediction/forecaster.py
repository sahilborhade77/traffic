#!/usr/bin/env python3
"""
Traffic Density Forecaster

High-level interface for traffic density prediction using LSTM models.
Provides easy-to-use methods for training and prediction.
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import time

from .traffic_density_predictor import TrafficDensityPredictor

logger = logging.getLogger(__name__)

class TrafficForecaster:
    """
    High-level traffic density forecasting interface.
    """

    def __init__(self,
                 model_path: Optional[str] = None,
                 input_size: int = 4,
                 seq_length: int = 60,
                 pred_length: int = 15):
        """
        Initialize forecaster.

        Args:
            model_path: Path to pre-trained model (optional)
            input_size: Number of input features (lanes)
            seq_length: Input sequence length (minutes)
            pred_length: Prediction horizon (minutes)
        """
        self.input_size = input_size
        self.seq_length = seq_length
        self.pred_length = pred_length

        # Initialize predictor
        self.predictor = TrafficDensityPredictor(
            input_size=input_size,
            seq_length=seq_length,
            pred_length=pred_length
        )

        # Load model if provided
        if model_path and Path(model_path).exists():
            self.predictor.load_model(model_path)
            logger.info(f"Loaded model from {model_path}")
        else:
            logger.warning("No model loaded - call train() or load_model() first")

    def train(self,
              csv_path: str,
              model_save_path: str = 'models/traffic_density_lstm.pth',
              epochs: int = 100,
              batch_size: int = 32) -> Dict[str, Any]:
        """
        Train the forecasting model.

        Args:
            csv_path: Path to training data CSV
            model_save_path: Path to save trained model
            epochs: Number of training epochs
            batch_size: Training batch size

        Returns:
            Training results and metrics
        """
        from .traffic_density_predictor import train_traffic_density_predictor

        logger.info("Starting model training...")

        # Train the predictor
        trained_predictor = train_traffic_density_predictor(
            csv_path=csv_path,
            model_save_path=model_save_path,
            epochs=epochs,
            batch_size=batch_size
        )

        # Update our predictor instance
        self.predictor = trained_predictor

        # Load the saved model to ensure consistency
        self.predictor.load_model(model_save_path)

        logger.info("Training completed and model loaded")

        return {
            'model_path': model_save_path,
            'input_size': self.input_size,
            'seq_length': self.seq_length,
            'pred_length': self.pred_length,
            'status': 'trained'
        }

    def predict_next_15_minutes(self, recent_data: np.ndarray) -> Dict[str, Any]:
        """
        Predict traffic density for the next 15 minutes.

        Args:
            recent_data: Recent traffic data of shape (seq_length, input_size)
                         Should contain density data for each lane

        Returns:
            Prediction results with timestamps and confidence
        """
        if recent_data.shape != (self.seq_length, self.input_size):
            raise ValueError(f"Recent data must be shape ({self.seq_length}, {self.input_size}), "
                           f"got {recent_data.shape}")

        # Make prediction
        predictions = self.predictor.predict(recent_data)

        # Generate timestamps (assuming 1-minute intervals)
        current_time = pd.Timestamp.now()
        timestamps = pd.date_range(
            start=current_time + pd.Timedelta(minutes=1),
            end=current_time + pd.Timedelta(minutes=self.pred_length),
            freq='1min'
        )

        # Format results
        results = {
            'predictions': predictions.tolist(),
            'timestamps': timestamps.strftime('%Y-%m-%d %H:%M:%S').tolist(),
            'lanes': [f'lane_{i+1}' for i in range(self.input_size)],
            'prediction_horizon_minutes': self.pred_length,
            'input_sequence_length': self.seq_length,
            'generated_at': current_time.strftime('%Y-%m-%d %H:%M:%S')
        }

        logger.info(f"Generated {self.pred_length}-minute predictions")

        return results

    def predict_from_csv(self,
                        csv_path: str,
                        num_recent_minutes: Optional[int] = None) -> Dict[str, Any]:
        """
        Predict using recent data from CSV file.

        Args:
            csv_path: Path to CSV file with traffic data
            num_recent_minutes: Number of recent minutes to use (default: seq_length)

        Returns:
            Prediction results
        """
        if not Path(csv_path).exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        # Load data
        df = pd.read_csv(csv_path)

        # Find density columns
        density_cols = [col for col in df.columns if 'density' in col.lower()]
        if not density_cols:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            density_cols = list(numeric_cols[:self.input_size])

        if len(density_cols) < self.input_size:
            raise ValueError(f"Need at least {self.input_size} density columns")

        # Use most recent data
        recent_data = df[density_cols[:self.input_size]].values

        if len(recent_data) < self.seq_length:
            raise ValueError(f"Need at least {self.seq_length} data points, got {len(recent_data)}")

        # Use specified number of recent minutes or default to seq_length
        num_minutes = num_recent_minutes or self.seq_length
        recent_data = recent_data[-num_minutes:]

        # Pad if necessary
        if len(recent_data) < self.seq_length:
            # Repeat last value to pad
            padding = np.tile(recent_data[-1:], (self.seq_length - len(recent_data), 1))
            recent_data = np.vstack([padding, recent_data])

        return self.predict_next_15_minutes(recent_data)

    def get_prediction_summary(self, predictions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a summary of prediction results.

        Args:
            predictions: Prediction results from predict_next_15_minutes

        Returns:
            Summary statistics
        """
        pred_array = np.array(predictions['predictions'])

        summary = {
            'total_vehicles_predicted': {
                lane: float(pred_array[:, i].sum())
                for i, lane in enumerate(predictions['lanes'])
            },
            'peak_density_minute': {
                lane: int(np.argmax(pred_array[:, i])) + 1
                for i, lane in enumerate(predictions['lanes'])
            },
            'average_density': {
                lane: float(pred_array[:, i].mean())
                for i, lane in enumerate(predictions['lanes'])
            },
            'max_density': {
                lane: float(pred_array[:, i].max())
                for i, lane in enumerate(predictions['lanes'])
            },
            'prediction_range': {
                'start': predictions['timestamps'][0],
                'end': predictions['timestamps'][-1]
            }
        }

        return summary

    def load_model(self, model_path: str):
        """
        Load a pre-trained model.

        Args:
            model_path: Path to model checkpoint
        """
        self.predictor.load_model(model_path)
        logger.info(f"Model loaded from {model_path}")

# Legacy function for backward compatibility
def predict_congestion(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Legacy prediction function for backward compatibility.

    Args:
        data: Dictionary containing traffic data

    Returns:
        Prediction results (placeholder for now)
    """
    logger.warning("Using legacy predict_congestion function. Consider using TrafficForecaster class instead.")

    # Try to extract density data from input
    if 'recent_densities' in data:
        densities = np.array(data['recent_densities'])
        if densities.shape[0] >= 60:  # Assume 60-minute sequence
            forecaster = TrafficForecaster()
            try:
                return forecaster.predict_next_15_minutes(densities[-60:])
            except Exception as e:
                logger.error(f"Prediction failed: {e}")

    # Fallback
    return {
        'status': 'error',
        'message': 'Insufficient data for prediction',
        'predictions': [],
        'timestamps': []
    }

# Example usage
if __name__ == "__main__":
    # Initialize forecaster
    forecaster = TrafficForecaster()

    # Train model (uncomment to train)
    # results = forecaster.train('data/traffic_analytics.csv')

    # Load existing model
    try:
        forecaster.load_model('models/traffic_density_lstm.pth')

        # Example prediction with synthetic data
        recent_data = np.random.rand(60, 4) * 20  # 60 minutes, 4 lanes, max 20 vehicles
        predictions = forecaster.predict_next_15_minutes(recent_data)

        print("15-minute traffic density predictions:")
        for i, (timestamp, densities) in enumerate(zip(predictions['timestamps'], predictions['predictions'])):
            print(f"{timestamp}: {densities}")

        # Get summary
        summary = forecaster.get_prediction_summary(predictions)
        print(f"\nPrediction Summary: {summary}")

    except Exception as e:
        print(f"Example failed: {e}")
