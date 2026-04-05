import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random
from collections import deque
import logging
try:
    import mlflow
except ImportError:
    mlflow = None

logger = logging.getLogger(__name__)

if mlflow:
    mlflow.set_experiment("Smart-Traffic-Signal-Control")

# --- Rule Based Agents ---

class RuleBasedAgent:
    """
    Baseline: Longest-Queue-First (LQF).
    """
    def __init__(self, action_space):
        self.action_space = action_space

    def get_action(self, state):
        # State: [q0, q1, q2, q3, current_phase]
        queues = state[:self.action_space]
        return np.argmax(queues)

# --- DQN Agent ---

class QNetwork(nn.Module):
    """Simple Neural Network for Q-Learning."""
    def __init__(self, state_dim, action_dim):
        super(QNetwork, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(state_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim)
        )

    def forward(self, x):
        return self.fc(x)

class DQNAgent:
    """
    Deep Q-Network (DQN) Agent.
    Learns to map states to best actions using experience replay.
    """
    def __init__(self, state_dim, action_dim, lr=1e-3, gamma=0.95, epsilon=1.0, epsilon_decay=0.995):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = 0.01
        self.epsilon_decay = epsilon_decay
        
        # Hardware Detection
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"DQN Agent initializing on {self.device}")
        
        self.memory = deque(maxlen=2000)
        self.model = QNetwork(state_dim, action_dim).to(self.device)
        self.optimizer = optim.Adam(self.model.parameters(), lr=lr)
        self.criterion = nn.MSELoss()

    def get_action(self, state, train=True):
        """Epsilon-greedy selection."""
        if train and random.random() < self.epsilon:
            return random.randrange(self.action_dim)
        
        state_t = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        with torch.no_grad():
            q_values = self.model(state_t)
        return torch.argmax(q_values).item()

    def store_experience(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def train(self, batch_size=32):
        if len(self.memory) < batch_size:
            return
        
        batch = random.sample(self.memory, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        
        states = torch.FloatTensor(np.array(states)).to(self.device)
        actions = torch.LongTensor(actions).unsqueeze(1).to(self.device)
        rewards = torch.FloatTensor(rewards).unsqueeze(1).to(self.device)
        next_states = torch.FloatTensor(np.array(next_states)).to(self.device)
        dones = torch.FloatTensor(dones).unsqueeze(1).to(self.device)
        
        # 1. Predicted Q values
        current_q = self.model(states).gather(1, actions)
        
        # 2. Target Q values (Bellman)
        with torch.no_grad():
            next_q = self.model(next_states).max(1)[0].unsqueeze(1)
            target_q = rewards + (1 - dones) * self.gamma * next_q
            
        # 3. Loss & Optimize
        loss = self.criterion(current_q, target_q)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        # 4. Expert Insight: Log to MLflow
        if mlflow and random.random() < 0.1: # Only log 10% to save memory 
            with mlflow.start_run(nested=True):
                mlflow.log_metric("dqn_loss", loss.item())
                mlflow.log_metric("epsilon", self.epsilon)
            
        # 5. Decay Epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
            
    def save(self, path):
        torch.save(self.model.state_dict(), path)
        logger.info(f"Model saved to {path}")

    def load(self, path):
        self.model.load_state_dict(torch.load(path))
        self.model.eval()
        logger.info(f"Model loaded from {path}")
