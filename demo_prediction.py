import os
import argparse
import pandas as pd
import numpy as np
import torch
import logging
from src.prediction.dataset import prepare_traffic_data
from src.prediction.model import LSTMForecaster, TrafficTrainer, MovingAverageBaseline
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def generate_synthetic_traffic(size=1000):
    """
    Generate synthetic traffic data with daily seasonality and noise.
    """
    logger.info(f"Generating {size} steps of synthetic traffic data...")
    time = np.linspace(0, 48 * np.pi, size) # Simulating 24 steps per cycle
    
    # Base pattern (Morning & Evening peaks)
    base_traffic = 20 + 30 * np.sin(time)**2 
    
    # Trend (Increasing traffic over time)
    trend = 0.01 * np.arange(size)
    
    # Noise
    noise = np.random.normal(0, 5, size)
    
    total_count = np.clip(base_traffic + trend + noise, 0, 100)
    
    df = pd.DataFrame({
        'timestamp': pd.date_range(start='2024-01-01', periods=size, freq='H'),
        'total_count': total_count
    })
    return df

def main():
    parser = argparse.ArgumentParser(description="Module 3: Traffic Flow Prediction Demo")
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs")
    parser.add_argument("--window", type=int, default=12, help="Number of past hours to look at")
    parser.add_argument("--horizon", type=int, default=1, help="Number of hours to predict in future")
    parser.add_argument("--save", default="models/traffic_lstm.pth", help="Path to save the model")
    
    args = parser.parse_args()
    os.makedirs('models', exist_ok=True)
    os.makedirs('data', exist_ok=True)

    # Step 1: Prep Data
    df = generate_synthetic_traffic(size=1000)
    train_loader, val_loader, test_loader, scaler = prepare_traffic_data(
        df, column='total_count', window_size=args.window, horizon=args.horizon
    )

    # Step 2: Init and Train LSTM
    logger.info("Initializing LSTM model...")
    model = LSTMForecaster(input_dim=1, hidden_dim=64, num_layers=2)
    trainer = TrafficTrainer(model)

    for epoch in range(args.epochs):
        train_loss = trainer.train_epoch(train_loader)
        val_loss = trainer.evaluate(val_loader)
        
        if (epoch + 1) % 10 == 0:
            logger.info(f"Epoch {epoch+1} -> Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}")

    # Step 3: Evaluations
    logger.info("Starting Comparative Evaluation...")
    
    # 3.1. Evaluate LSTM
    model.eval()
    all_preds, all_actual = [], []
    with torch.no_grad():
        for X, y in test_loader:
            outputs = model(X)
            all_preds.extend(outputs.numpy())
            all_actual.extend(y.numpy())
    
    # Inverse scale for real-world interpretation
    preds_orig = scaler.inverse_transform(np.array(all_preds).reshape(-1, 1))
    actual_orig = scaler.inverse_transform(np.array(all_actual).reshape(-1, 1))
    
    # 3.2. Evaluate Baseline (Moving Average)
    baseline = MovingAverageBaseline(window_size=args.window)
    last_window_test = df['total_count'].values[-len(all_actual)-args.window:]
    baseline_preds = [np.mean(last_window_test[i:i+args.window]) for i in range(len(all_actual))]

    # Step 4: Metrics
    lstm_mae = mean_absolute_error(actual_orig, preds_orig)
    lstm_rmse = np.sqrt(mean_squared_error(actual_orig, preds_orig))
    
    base_mae = mean_absolute_error(actual_orig, baseline_preds)
    base_rmse = np.sqrt(mean_squared_error(actual_orig, baseline_preds))

    logger.info("-" * 30)
    logger.info("PREDICTION RESULTS")
    logger.info("-" * 30)
    logger.info(f"LSTM -> MAE: {lstm_mae:.2f} | RMSE: {lstm_rmse:.2f}")
    logger.info(f"Baseline -> MAE: {base_mae:.2f} | RMSE: {base_rmse:.2f}")
    
    # Step 5: Save
    torch.save(model.state_dict(), args.save)
    logger.info(f"Model saved to {args.save}")

    # Save predictions
    results_df = pd.DataFrame({
        'Actual': actual_orig.flatten(),
        'LSTM_Pred': preds_orig.flatten(),
        'Baseline_Pred': baseline_preds
    })
    results_df.to_csv("data/prediction_results.csv", index=False)
    logger.info("Saved prediction results to data/prediction_results.csv")

if __name__ == "__main__":
    main()
