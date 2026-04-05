import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import logging

logger = logging.getLogger(__name__)

# --- Baseline ---

class MovingAverageBaseline:
    """
    Very simple baseline using moving average.
    """
    def __init__(self, window_size):
        self.window_size = window_size

    def predict(self, window):
        return np.mean(window, axis=0)

# --- LSTM Network ---

class TrafficFlowPredictor(nn.Module):
    """
    Advanced LSTM Predictor with Dropout and Linear Layer Sequence.
    Simultaneously predicts density for all 4 lanes.
    """
    def __init__(self, input_size=4, hidden_size=128, num_layers=2, output_size=4):
        super(TrafficFlowPredictor, self).__init__()
        
        self.lstm = nn.LSTM(
            input_size=input_size,  # 4 lanes simultaneously
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.2
        )
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, output_size)  # Predict all 4 lane densities together
        )
    
    def forward(self, x):
        # x shape: (batch, sequence_length, input_size)
        lstm_out, _ = self.lstm(x)
        # Take last time step output (many-to-one architecture)
        last_output = lstm_out[:, -1, :]
        predictions = self.fc(last_output)
        return predictions

def predict_congestion(model, recent_data):
    """Predict traffic density for next 2-minute horizon"""
    model.eval()
    with torch.no_grad():
        recent_tensor = torch.FloatTensor(recent_data).unsqueeze(0)
        predicted_density = model(recent_tensor)
    
    return predicted_density.numpy()[0]

class TrafficTrainer:
    """
    Handles Training, Valuation and Prediction loops.
    """
    def __init__(self, model, lr=1e-3):
        self.model = model
        self.criterion = nn.MSELoss()
        self.optimizer = optim.Adam(model.parameters(), lr=lr)

    def train_epoch(self, train_loader):
        self.model.train()
        total_loss = 0
        for batch_X, batch_y in train_loader:
            self.optimizer.zero_grad()
            outputs = self.model(batch_X)
            loss = self.criterion(outputs, batch_y)
            loss.backward()
            self.optimizer.step()
            total_loss += loss.item()
        return total_loss / len(train_loader)

    def evaluate(self, val_loader):
        self.model.eval()
        total_loss = 0
        with torch.no_grad():
            for batch_X, batch_y in val_loader:
                outputs = self.model(batch_X)
                loss = self.criterion(outputs, batch_y)
                total_loss += loss.item()
        return total_loss / len(val_loader)
