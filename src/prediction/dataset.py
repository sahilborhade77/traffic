import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import MinMaxScaler
import logging

logger = logging.getLogger(__name__)

class TrafficDataset(Dataset):
    """
    Custom Dataset for Time-Series Traffic Prediction.
    """
    def __init__(self, data, window_size=10, horizon=1):
        """
        :param data: Numpy array of normalized traffic counts
        :param window_size: Number of past steps to look at (X)
        :param horizon: Number of steps to predict in future (y)
        """
        self.X, self.y = self._create_windows(data, window_size, horizon)
        
    def _create_windows(self, data, window_size, horizon):
        X, y = [], []
        for i in range(len(data) - window_size - horizon + 1):
            X.append(data[i:i + window_size])
            y.append(data[i + window_size + horizon - 1])
        return torch.tensor(np.array(X), dtype=torch.float32), torch.tensor(np.array(y), dtype=torch.float32)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

def prepare_traffic_data(df, column='total_count', window_size=10, horizon=1, batch_size=32):
    """
    Preprocess data and create DataLoaders.
    """
    # 1. Scale data
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(df[[column]].values)
    
    # 2. Split (Train 70%, Val 15%, Test 15%)
    n = len(scaled_data)
    train_end = int(n * 0.7)
    val_end = int(n * 0.85)
    
    train_data = scaled_data[:train_end]
    val_data = scaled_data[train_end:val_end]
    test_data = scaled_data[val_end:]
    
    # 3. Create Datasets
    train_ds = TrafficDataset(train_data, window_size, horizon)
    val_ds = TrafficDataset(val_data, window_size, horizon)
    test_ds = TrafficDataset(test_data, window_size, horizon)
    
    # 4. Create Loaders
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size)
    test_loader = DataLoader(test_ds, batch_size=batch_size)
    
    return train_loader, val_loader, test_loader, scaler
