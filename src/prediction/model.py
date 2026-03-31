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

class LSTMForecaster(nn.Module):
    """
    Long Short-Term Memory (LSTM) for traffic prediction.
    """
    def __init__(self, input_dim=1, hidden_dim=64, num_layers=2, output_dim=1):
        super(LSTMForecaster, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # LSTM Layer
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
        
        # Output layers
        self.fc = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        # x shape: (batch, seq_len, features)
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim)
        
        # Pass through LSTM
        out, _ = self.lstm(x, (h0, c0))
        
        # Take the last hidden state
        # out shape: (batch, seq_len, hidden_dim)
        out = out[:, -1, :]
        
        # Final prediction
        out = self.fc(out)
        return out

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
