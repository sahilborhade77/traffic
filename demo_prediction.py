#!/usr/bin/env python3
"""
Traffic Density Prediction Demo

Demonstrates the LSTM-based traffic density prediction system.
Shows training pipeline and real-time prediction capabilities.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import logging
import time
from pathlib import Path
import sys
import os
from typing import Optional

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from prediction.traffic_density_predictor import TrafficDensityPredictor, train_traffic_density_predictor
from prediction.forecaster import TrafficForecaster

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_synthetic_traffic_data(num_samples: int = 1000, save_path: str = 'data/traffic_analytics.csv'):
    """
    Generate synthetic traffic data for demonstration.

    Args:
        num_samples: Number of data points to generate
        save_path: Path to save the generated data
    """
    logger.info(f"Generating {num_samples} synthetic traffic data points...")

    # Create timestamps
    start_time = pd.Timestamp('2024-01-01 06:00:00')  # Start at 6 AM
    timestamps = pd.date_range(start=start_time, periods=num_samples, freq='1min')

    # Generate traffic patterns based on time of day
    hours = timestamps.hour + timestamps.minute / 60.0

    # Morning rush hour (7-9 AM): high traffic
    morning_rush = ((hours >= 7) & (hours <= 9)).astype(float)

    # Evening rush hour (5-7 PM): high traffic
    evening_rush = ((hours >= 17) & (hours <= 19)).astype(float)

    # Lunch time (12-2 PM): moderate traffic
    lunch_time = ((hours >= 12) & (hours <= 14)).astype(float)

    # Base traffic level
    base_traffic = 5 + 3 * np.sin(2 * np.pi * hours / 24)  # Daily cycle

    # Add rush hour peaks
    traffic_multiplier = 1 + 2 * morning_rush + 2 * evening_rush + 0.5 * lunch_time

    # Generate density for 4 lanes
    np.random.seed(42)  # For reproducible results

    data = []
    for i in range(num_samples):
        # Base density with time-based variation
        base_density = base_traffic[i] * traffic_multiplier[i]

        # Add some randomness and lane-specific patterns
        lane_densities = []
        for lane in range(4):
            # Different lanes have slightly different patterns
            lane_factor = 1 + 0.2 * np.sin(2 * np.pi * (hours[i] + lane) / 24)
            noise = np.random.normal(0, 1)
            density = max(0, base_density * lane_factor + noise)
            lane_densities.append(density)

        data.append(lane_densities)

    # Create DataFrame
    df = pd.DataFrame(data, columns=['lane_1_density', 'lane_2_density', 'lane_3_density', 'lane_4_density'])
    df['timestamp'] = timestamps

    # Save to CSV
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    df.to_csv(save_path, index=False)

    logger.info(f"Synthetic data saved to {save_path}")
    logger.info(f"Data shape: {df.shape}")
    logger.info(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    return df

def plot_traffic_patterns(df: pd.DataFrame, save_path: Optional[str] = None):
    """
    Plot traffic patterns over time.

    Args:
        df: DataFrame with traffic data
        save_path: Optional path to save plot
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

    # Plot all lanes
    density_cols = [col for col in df.columns if 'density' in col]
    df[density_cols].plot(ax=ax1, alpha=0.7)
    ax1.set_title('Traffic Density by Lane')
    ax1.set_xlabel('Time (minutes)')
    ax1.set_ylabel('Vehicle Density')
    ax1.legend()
    ax1.grid(True)

    # Plot hourly averages
    df['hour'] = df['timestamp'].dt.hour
    hourly_avg = df.groupby('hour')[density_cols].mean()
    hourly_avg.plot(ax=ax2, marker='o')
    ax2.set_title('Average Traffic Density by Hour')
    ax2.set_xlabel('Hour of Day')
    ax2.set_ylabel('Average Vehicle Density')
    ax2.legend()
    ax2.grid(True)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Traffic pattern plot saved to {save_path}")

    plt.show()

def demo_training_pipeline():
    """
    Demonstrate the complete training pipeline.
    """
    logger.info("=== Training Pipeline Demo ===")

    # Generate synthetic data if it doesn't exist
    data_path = 'data/traffic_analytics.csv'
    if not Path(data_path).exists():
        df = generate_synthetic_traffic_data(2000, data_path)
        plot_traffic_patterns(df, 'data/traffic_patterns.png')
    else:
        logger.info(f"Using existing data from {data_path}")

    # Train the model
    logger.info("Training LSTM model...")
    predictor = train_traffic_density_predictor(
        csv_path=data_path,
        model_save_path='models/traffic_density_lstm.pth',
        epochs=20,  # Reduced for demo
        batch_size=16
    )

    logger.info("Training completed!")
    return predictor

def demo_prediction(predictor: TrafficDensityPredictor):
    """
    Demonstrate prediction capabilities.
    """
    logger.info("=== Prediction Demo ===")

    # Load recent data for prediction
    df = pd.read_csv('data/traffic_analytics.csv')
    density_cols = [col for col in df.columns if 'density' in col]

    # Use last 60 minutes as input
    recent_data = df[density_cols].values[-60:]

    logger.info(f"Using last {len(recent_data)} minutes of data for prediction")

    # Make prediction
    predictions = predictor.predict(recent_data)

    logger.info(f"Predicted densities for next {len(predictions)} minutes:")
    for i, pred in enumerate(predictions):
        logger.info(f"Minute {i+1}: {pred}")

    # Plot predictions
    plt.figure(figsize=(10, 6))
    plt.plot(range(1, len(predictions) + 1), predictions[:, 0], 'b-', label='Lane 1', marker='o')
    plt.plot(range(1, len(predictions) + 1), predictions[:, 1], 'r-', label='Lane 2', marker='s')
    plt.plot(range(1, len(predictions) + 1), predictions[:, 2], 'g-', label='Lane 3', marker='^')
    plt.plot(range(1, len(predictions) + 1), predictions[:, 3], 'm-', label='Lane 4', marker='d')

    plt.title('15-Minute Traffic Density Predictions')
    plt.xlabel('Minutes Ahead')
    plt.ylabel('Predicted Vehicle Density')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('data/prediction_demo.png', dpi=300, bbox_inches='tight')
    plt.show()

    logger.info("Prediction plot saved to data/prediction_demo.png")

def demo_forecaster_interface():
    """
    Demonstrate the high-level forecaster interface.
    """
    logger.info("=== Forecaster Interface Demo ===")

    # Initialize forecaster
    forecaster = TrafficForecaster(model_path='models/traffic_density_lstm.pth')

    # Generate some test data
    recent_data = np.random.rand(60, 4) * 15  # 60 minutes, 4 lanes

    # Make prediction
    results = forecaster.predict_next_15_minutes(recent_data)

    logger.info("Forecaster prediction results:")
    logger.info(f"Generated at: {results['generated_at']}")
    logger.info(f"Prediction horizon: {results['prediction_horizon_minutes']} minutes")

    for timestamp, densities in zip(results['timestamps'][:5], results['predictions'][:5]):
        logger.info(f"{timestamp}: {densities}")

    # Get summary
    summary = forecaster.get_prediction_summary(results)
    logger.info(f"Prediction summary: {summary}")

def benchmark_prediction_speed(predictor: TrafficDensityPredictor, num_runs: int = 100):
    """
    Benchmark prediction speed.

    Args:
        predictor: Trained predictor instance
        num_runs: Number of prediction runs to average
    """
    logger.info(f"=== Prediction Speed Benchmark ({num_runs} runs) ===")

    # Generate test data
    test_data = np.random.rand(60, 4)

    # Warm up
    for _ in range(5):
        _ = predictor.predict(test_data)

    # Benchmark
    start_time = time.time()
    for _ in range(num_runs):
        _ = predictor.predict(test_data)
    end_time = time.time()

    avg_time = (end_time - start_time) / num_runs * 1000  # Convert to milliseconds

    logger.info(f"Average prediction time: {avg_time:.2f} ms")
    logger.info(f"Predictions per second: {1000 / avg_time:.1f}")

def main():
    """
    Main demo function.
    """
    logger.info("Starting Traffic Density Prediction Demo")

    try:
        # Demo 1: Training pipeline
        predictor = demo_training_pipeline()

        # Demo 2: Prediction capabilities
        demo_prediction(predictor)

        # Demo 3: High-level interface
        demo_forecaster_interface()

        # Demo 4: Performance benchmark
        benchmark_prediction_speed(predictor)

        logger.info("=== Demo completed successfully! ===")
        logger.info("Check the following files:")
        logger.info("- models/traffic_density_lstm.pth (trained model)")
        logger.info("- data/traffic_patterns.png (traffic patterns plot)")
        logger.info("- data/prediction_demo.png (prediction results plot)")

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise

if __name__ == "__main__":
    main()
