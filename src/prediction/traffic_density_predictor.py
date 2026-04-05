#!/usr/bin/env python3
"""
Traffic Density LSTM Predictor

LSTM model for predicting traffic density patterns 15 minutes into the future
based on historical vehicle count data, with complete training pipeline.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
import logging
from typing import Tuple, List, Dict, Optional, Any
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import matplotlib.pyplot as plt
import os
import time

logger = logging.getLogger(__name__)

class TrafficDensityDataset(Dataset):
    """
    Dataset for traffic density time series prediction.
    """

    def __init__(self, data: np.ndarray, seq_length: int = 60, pred_length: int = 15):
        """
        Initialize dataset.

        Args:
            data: Time series data of shape (time_steps, features)
            seq_length: Length of input sequence (history window)
            pred_length: Length of prediction horizon
        """
        self.data = torch.FloatTensor(data)
        self.seq_length = seq_length
        self.pred_length = pred_length

    def __len__(self) -> int:
        return len(self.data) - self.seq_length - self.pred_length + 1

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        # Input sequence
        x = self.data[idx:idx + self.seq_length]

        # Target sequence (next pred_length steps)
        y = self.data[idx + self.seq_length:idx + self.seq_length + self.pred_length]

        return x, y

class TrafficDensityLSTM(nn.Module):
    """
    LSTM model for multi-step traffic density prediction.
    """

    def __init__(self,
                 input_size: int = 4,
                 hidden_size: int = 128,
                 num_layers: int = 2,
                 output_size: int = 4,
                 pred_length: int = 15,
                 dropout: float = 0.2):
        """
        Initialize LSTM model.

        Args:
            input_size: Number of input features (lanes)
            hidden_size: LSTM hidden size
            num_layers: Number of LSTM layers
            output_size: Number of output features (lanes)
            pred_length: Prediction horizon (15 minutes)
            dropout: Dropout rate
        """
        super(TrafficDensityLSTM, self).__init__()

        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.output_size = output_size
        self.pred_length = pred_length

        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )

        # Attention mechanism for better long-term dependencies
        self.attention = nn.Linear(hidden_size, 1)

        # Output layers for multi-step prediction
        self.fc_layers = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_size, hidden_size // 2),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_size // 2, output_size)
            ) for _ in range(pred_length)
        ])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Input tensor of shape (batch, seq_length, input_size)

        Returns:
            Output tensor of shape (batch, pred_length, output_size)
        """
        # LSTM forward
        lstm_out, (h_n, c_n) = self.lstm(x)

        # Apply attention to LSTM outputs
        attention_weights = torch.softmax(self.attention(lstm_out), dim=1)
        context = torch.sum(attention_weights * lstm_out, dim=1)

        # Multi-step prediction
        predictions = []
        for i in range(self.pred_length):
            pred = self.fc_layers[i](context)
            predictions.append(pred)

        # Stack predictions
        output = torch.stack(predictions, dim=1)

        return output

class TrafficDensityPredictor:
    """
    Complete traffic density prediction system with LSTM model and training pipeline.
    """

    def __init__(self,
                 input_size: int = 4,
                 hidden_size: int = 128,
                 num_layers: int = 2,
                 seq_length: int = 60,
                 pred_length: int = 15,
                 learning_rate: float = 1e-3,
                 device: str = 'auto'):
        """
        Initialize predictor.

        Args:
            input_size: Number of input features (lanes)
            hidden_size: LSTM hidden size
            num_layers: Number of LSTM layers
            seq_length: Input sequence length (minutes)
            pred_length: Prediction horizon (minutes)
            learning_rate: Learning rate for training
            device: Device to run on ('auto', 'cpu', 'cuda')
        """
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.seq_length = seq_length
        self.pred_length = pred_length
        self.learning_rate = learning_rate

        # Device setup
        if device == 'auto':
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)

        # Model
        self.model = TrafficDensityLSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            output_size=input_size,
            pred_length=pred_length
        ).to(self.device)

        # Scaler for data normalization
        self.scaler = StandardScaler()

        # Training components
        self.criterion = nn.MSELoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='min', factor=0.5, patience=5, verbose=True
        )

        logger.info(f"Initialized TrafficDensityPredictor on {self.device}")

    def load_and_preprocess_data(self, csv_path: str) -> Tuple[np.ndarray, List[str]]:
        """
        Load and preprocess traffic data from CSV.

        Args:
            csv_path: Path to CSV file with traffic data

        Returns:
            Preprocessed data array and feature names
        """
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Data file not found: {csv_path}")

        # Load data
        df = pd.read_csv(csv_path)

        # Find density columns
        density_cols = [col for col in df.columns if 'density' in col.lower()]
        if not density_cols:
            # Fallback to any numeric columns that might be density data
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            density_cols = list(numeric_cols[:self.input_size])

        if len(density_cols) < self.input_size:
            raise ValueError(f"Need at least {self.input_size} density columns, found {len(density_cols)}")

        # Use first input_size columns
        feature_cols = density_cols[:self.input_size]
        data = df[feature_cols].values

        # Handle missing values
        data = pd.DataFrame(data).fillna(method='ffill').fillna(method='bfill').fillna(0).values

        # Normalize data
        data = self.scaler.fit_transform(data)

        logger.info(f"Loaded data shape: {data.shape}, features: {feature_cols}")

        return data, feature_cols

    def create_data_loaders(self,
                           data: np.ndarray,
                           batch_size: int = 32,
                           train_split: float = 0.7,
                           val_split: float = 0.2) -> Tuple[DataLoader, DataLoader, DataLoader]:
        """
        Create train/validation/test data loaders.

        Args:
            data: Preprocessed data array
            batch_size: Batch size for data loaders
            train_split: Fraction of data for training
            val_split: Fraction of data for validation

        Returns:
            Train, validation, and test data loaders
        """
        # Create dataset
        dataset = TrafficDensityDataset(data, self.seq_length, self.pred_length)

        # Split indices
        total_size = len(dataset)
        train_size = int(total_size * train_split)
        val_size = int(total_size * val_split)
        test_size = total_size - train_size - val_size

        # Create subsets
        train_dataset = torch.utils.data.Subset(dataset, range(train_size))
        val_dataset = torch.utils.data.Subset(dataset, range(train_size, train_size + val_size))
        test_dataset = torch.utils.data.Subset(dataset, range(train_size + val_size, total_size))

        # Create data loaders
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
        test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

        logger.info(f"Created data loaders: Train={len(train_dataset)}, Val={len(val_dataset)}, Test={len(test_dataset)}")

        return train_loader, val_loader, test_loader

    def train(self,
              train_loader: DataLoader,
              val_loader: DataLoader,
              epochs: int = 100,
              patience: int = 10,
              save_path: Optional[str] = None) -> Dict[str, List[float]]:
        """
        Train the LSTM model.

        Args:
            train_loader: Training data loader
            val_loader: Validation data loader
            epochs: Maximum number of epochs
            patience: Early stopping patience
            save_path: Path to save best model

        Returns:
            Training history
        """
        logger.info("Starting training...")

        history = {
            'train_loss': [],
            'val_loss': [],
            'learning_rate': []
        }

        best_val_loss = float('inf')
        patience_counter = 0

        for epoch in range(epochs):
            # Training phase
            self.model.train()
            train_loss = 0.0

            for batch_x, batch_y in train_loader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)

                self.optimizer.zero_grad()
                outputs = self.model(batch_x)
                loss = self.criterion(outputs, batch_y)
                loss.backward()
                self.optimizer.step()

                train_loss += loss.item()

            train_loss /= len(train_loader)

            # Validation phase
            self.model.eval()
            val_loss = 0.0

            with torch.no_grad():
                for batch_x, batch_y in val_loader:
                    batch_x = batch_x.to(self.device)
                    batch_y = batch_y.to(self.device)

                    outputs = self.model(batch_x)
                    loss = self.criterion(outputs, batch_y)
                    val_loss += loss.item()

            val_loss /= len(val_loader)

            # Learning rate scheduling
            self.scheduler.step(val_loss)
            current_lr = self.optimizer.param_groups[0]['lr']

            # Record history
            history['train_loss'].append(train_loss)
            history['val_loss'].append(val_loss)
            history['learning_rate'].append(current_lr)

            logger.info(f"Epoch {epoch+1}/{epochs} - Train Loss: {train_loss:.4f}, "
                       f"Val Loss: {val_loss:.4f}, LR: {current_lr:.6f}")

            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0

                # Save best model
                if save_path:
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    torch.save({
                        'epoch': epoch,
                        'model_state_dict': self.model.state_dict(),
                        'optimizer_state_dict': self.optimizer.state_dict(),
                        'val_loss': val_loss,
                        'scaler': self.scaler
                    }, save_path)
                    logger.info(f"Saved best model to {save_path}")
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    logger.info(f"Early stopping at epoch {epoch+1}")
                    break

        logger.info("Training completed")
        return history

    def predict(self, input_sequence: np.ndarray) -> np.ndarray:
        """
        Make predictions for the next pred_length time steps.

        Args:
            input_sequence: Input sequence of shape (seq_length, input_size)

        Returns:
            Predictions of shape (pred_length, input_size)
        """
        self.model.eval()

        # Preprocess input
        if input_sequence.shape[1] != self.input_size:
            raise ValueError(f"Input sequence must have {self.input_size} features")

        # Normalize input
        input_normalized = self.scaler.transform(input_sequence)

        # Convert to tensor
        input_tensor = torch.FloatTensor(input_normalized).unsqueeze(0).to(self.device)

        # Make prediction
        with torch.no_grad():
            predictions = self.model(input_tensor)

        # Denormalize predictions
        predictions_np = predictions.cpu().numpy().squeeze(0)
        predictions_denorm = self.scaler.inverse_transform(predictions_np)

        return predictions_denorm

    def evaluate(self, test_loader: DataLoader) -> Dict[str, float]:
        """
        Evaluate model on test data.

        Args:
            test_loader: Test data loader

        Returns:
            Evaluation metrics
        """
        self.model.eval()
        predictions = []
        targets = []

        with torch.no_grad():
            for batch_x, batch_y in test_loader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)

                outputs = self.model(batch_x)

                predictions.extend(outputs.cpu().numpy())
                targets.extend(batch_y.cpu().numpy())

        # Denormalize
        predictions = np.array(predictions)
        targets = np.array(targets)

        # Reshape for scaler
        pred_shape = predictions.shape
        target_shape = targets.shape

        predictions_flat = predictions.reshape(-1, self.input_size)
        targets_flat = targets.reshape(-1, self.input_size)

        predictions_denorm = self.scaler.inverse_transform(predictions_flat)
        targets_denorm = self.scaler.inverse_transform(targets_flat)

        predictions_denorm = predictions_denorm.reshape(pred_shape)
        targets_denorm = targets_denorm.reshape(target_shape)

        # Calculate metrics
        mse = mean_squared_error(targets_denorm.flatten(), predictions_denorm.flatten())
        mae = mean_absolute_error(targets_denorm.flatten(), predictions_denorm.flatten())
        rmse = np.sqrt(mse)

        metrics = {
            'mse': mse,
            'mae': mae,
            'rmse': rmse
        }

        logger.info(f"Test Metrics - MSE: {mse:.4f}, MAE: {mae:.4f}, RMSE: {rmse:.4f}")

        return metrics

    def load_model(self, checkpoint_path: str):
        """
        Load model from checkpoint.

        Args:
            checkpoint_path: Path to model checkpoint
        """
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.scaler = checkpoint.get('scaler', StandardScaler())

        logger.info(f"Loaded model from {checkpoint_path}")

    def plot_training_history(self, history: Dict[str, List[float]], save_path: Optional[str] = None):
        """
        Plot training history.

        Args:
            history: Training history dictionary
            save_path: Optional path to save plot
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

        # Loss plot
        ax1.plot(history['train_loss'], label='Train Loss')
        ax1.plot(history['val_loss'], label='Validation Loss')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Loss')
        ax1.set_title('Training and Validation Loss')
        ax1.legend()
        ax1.grid(True)

        # Learning rate plot
        ax2.plot(history['learning_rate'])
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Learning Rate')
        ax2.set_title('Learning Rate Schedule')
        ax2.set_yscale('log')
        ax2.grid(True)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved training plot to {save_path}")

        plt.show()

# Training pipeline function
def train_traffic_density_predictor(csv_path: str,
                                   model_save_path: str = 'models/traffic_density_lstm.pth',
                                   epochs: int = 100,
                                   batch_size: int = 32) -> TrafficDensityPredictor:
    """
    Complete training pipeline for traffic density prediction.

    Args:
        csv_path: Path to training data CSV
        model_save_path: Path to save trained model
        epochs: Number of training epochs
        batch_size: Training batch size

    Returns:
        Trained predictor instance
    """
    logger.info("Starting traffic density predictor training pipeline")

    # Initialize predictor
    predictor = TrafficDensityPredictor()

    try:
        # Load and preprocess data
        logger.info("Loading and preprocessing data...")
        data, feature_names = predictor.load_and_preprocess_data(csv_path)

        # Create data loaders
        logger.info("Creating data loaders...")
        train_loader, val_loader, test_loader = predictor.create_data_loaders(
            data, batch_size=batch_size
        )

        # Train model
        logger.info("Training model...")
        history = predictor.train(
            train_loader, val_loader, epochs=epochs, save_path=model_save_path
        )

        # Evaluate on test set
        logger.info("Evaluating on test set...")
        test_metrics = predictor.evaluate(test_loader)

        # Plot training history
        try:
            predictor.plot_training_history(history, save_path=model_save_path.replace('.pth', '_training.png'))
        except:
            logger.warning("Could not create training plot")

        logger.info("Training pipeline completed successfully")
        logger.info(f"Test metrics: {test_metrics}")

        return predictor

    except Exception as e:
        logger.error(f"Training pipeline failed: {e}")
        raise

# Example usage
if __name__ == "__main__":
    # Example training
    try:
        predictor = train_traffic_density_predictor(
            csv_path='data/traffic_analytics.csv',
            model_save_path='models/traffic_density_lstm.pth',
            epochs=50,
            batch_size=16
        )

        # Example prediction
        # Load recent data and predict next 15 minutes
        recent_data = np.random.randn(60, 4)  # 60 minutes of 4-lane data
        predictions = predictor.predict(recent_data)

        print(f"Predictions shape: {predictions.shape}")
        print(f"Predicted densities for next 15 minutes:\n{predictions}")

    except Exception as e:
        print(f"Example failed: {e}")