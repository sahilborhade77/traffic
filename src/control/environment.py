import gymnasium as gym
from gymnasium import spaces
import numpy as np
import logging

logger = logging.getLogger(__name__)

class TrafficSignalEnv(gym.Env):
    """
    Advanced Gymnasium-compliant environment for AI Traffic Control.
    State: [Lane Densities (4), Current Phase, Time in Phase]
    Action: Discrete change to one of 4 signal phases.
    """
    def __init__(self, num_lanes=4):
        super(TrafficSignalEnv, self).__init__()
        
        # State: 4 lanes + current phase + time_in_phase
        self.observation_space = spaces.Box(
            low=0, high=100, shape=(6,), dtype=np.float32
        )
        
        # Action: Switch to phase 0, 1, 2, or 3
        self.action_space = spaces.Discrete(4)
        
        self.num_lanes = num_lanes
        self.max_steps = 1000
        self.min_green_time = 10
        self.max_green_time = 60
        
        # Internal State
        self.queues = np.zeros(num_lanes)
        self.current_phase = 0
        self.time_in_phase = 0
        self.step_count = 0
        
    def reset(self, seed=None, options=None):
        """Initializes a new training episode."""
        super().reset(seed=seed)
        self.queues = np.zeros(self.num_lanes)
        self.current_phase = 0
        self.time_in_phase = 0
        self.step_count = 0
        
        return self._get_obs(), {}

    def _get_obs(self):
        """Returns current state for the AI."""
        return np.array([
            self.queues[0], self.queues[1], self.queues[2], self.queues[3],
            float(self.current_phase),
            float(self.time_in_phase)
        ], dtype=np.float32)

    def step(self, action):
        """Advances the simulation by 1 second based on AI's action."""
        reward = 0
        terminated = False
        truncated = False
        
        # Logic: Switching Phases
        if action != self.current_phase:
            if self.time_in_phase >= self.min_green_time:
                # Valid switch: Reward for choosing a busy lane
                old_lane_density = self.queues[self.current_phase]
                new_lane_density = self.queues[action]
                if new_lane_density > old_lane_density:
                    reward += 5
                
                self.current_phase = action
                self.time_in_phase = 0
            else:
                # Penalty for switching too soon (premature switch)
                reward -= 10
        else:
            self.time_in_phase += 1
        
        # Simulated Traffic Movement (Discharge green lane, add random incoming)
        discharge = 2 if self.time_in_phase > 0 else 0
        self.queues[self.current_phase] = max(0, self.queues[self.current_phase] - discharge)
        
        # Random Car Arrivals (Simulating 4 random entries)
        arrivals = np.random.poisson(0.5, self.num_lanes)
        self.queues = np.clip(self.queues + arrivals, 0, 100)
        
        # Cumulative Penalty: Total cars waiting across all lanes
        reward -= np.sum(self.queues) * 0.1
        
        self.step_count += 1
        if self.step_count >= self.max_steps:
            terminated = True
            
        return self._get_obs(), float(reward), terminated, truncated, {}
