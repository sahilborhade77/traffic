import numpy as np
import torch
import pandas as pd
from torch.utils.data import Dataset, DataLoader

class TrafficSequenceDataset(Dataset):
    """
    Constructs overlapping (X, y) windows for traffic forecasting.
    :param data: Numpy array of shape (time_steps, lanes)
    :param history_window: Number of past time steps to look at (X)
    :param forecast_window: Number of future time steps to predict (y)
    """
    def __init__(self, data, history_window=60, forecast_window=12):
        self.data = torch.FloatTensor(data)
        self.history_window = history_window
        self.forecast_window = forecast_window

    def __len__(self):
        return len(self.data) - self.history_window - self.forecast_window

    def __getitem__(self, idx):
        # Input: The past 'history_window' (e.g. 10 mins)
        x = self.data[idx : idx + self.history_window]
        
        # Target: The density after 'forecast_window' (e.g. at 2 mins out)
        y = self.data[idx + self.history_window + self.forecast_window - 1]
        
        return x, y

def prepare_prediction_loaders(csv_path, history=60, forecast=12, batch_size=32):
    """
    Helper to load traffic analytics and create data loaders.
    Expects CSV from Vision module with '_density' columns.
    """
    df = pd.read_csv(csv_path)
    # Automatically find all density columns
    density_cols = [c for c in df.columns if '_density' in c]
    
    if len(density_cols) < 1:
        raise ValueError("No traffic density columns found in the dataset.")
        
    data_values = df[density_cols].values
    
    # Create dataset
    full_dataset = TrafficSequenceDataset(data_values, history, forecast)
    
    # Train/Test Split (80/20)
    train_size = int(0.8 * len(full_dataset))
    test_size = len(full_dataset) - train_size
    train_ds, test_ds = torch.utils.data.random_split(full_dataset, [train_size, test_size])
    
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)
    
    return train_loader, test_loader
