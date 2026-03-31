import numpy as np
import logging

logger = logging.getLogger(__name__)

class TrafficSignalEnv:
    """
    A simple custom environment for Traffic Signal Control.
    Simulates a 4-lane intersection (or N-lanes).
    """
    def __init__(self, num_lanes=4, max_queue=20):
        self.num_lanes = num_lanes
        self.max_queue = max_queue
        # Initial queues: [lane0, lane1, lane2, lane3]
        self.queues = np.zeros(num_lanes, dtype=int)
        self.current_green_lane = 0
        self.step_count = 0
        
    def reset(self):
        """Reset the environment to initial state."""
        self.queues = np.zeros(self.num_lanes, dtype=int)
        self.current_green_lane = 0
        self.step_count = 0
        return self.get_state()
    
    def get_state(self):
        """Returns the current state: queue lengths and active signal."""
        # Simple state representation: [queue0, queue1, ..., current_green_lane]
        return np.append(self.queues, [self.current_green_lane])

    def step(self, action, incoming_vehicles=None):
        """
        Takes an action and advances one simulation step.
        :param action: Index of the lane to give Green signal (0 to num_lanes-1)
        :param incoming_vehicles: List of new vehicles arriving in each lane (optional)
        :return: (next_state, reward, done, info)
        """
        # 1. Update Signal
        self.current_green_lane = action
        
        # 2. Process Outgoing (vehicles leave the green lane)
        # Assume 2 vehicles leave per step if the signal is green
        discharge_rate = 2
        departed = min(self.queues[action], discharge_rate)
        self.queues[action] -= departed
        
        # 3. Process Incoming (new arrivals)
        if incoming_vehicles is None:
            # Simulate random arrivals if no external data provided
            incoming_vehicles = np.random.poisson(0.5, self.num_lanes)
            
        self.queues = np.clip(self.queues + incoming_vehicles, 0, self.max_queue)
        
        # 4. Calculate Reward (Minimize total waiting time/queue length)
        # Penalty for every car waiting in every lane
        reward = -np.sum(self.queues)
        
        self.step_count += 1
        done = self.step_count >= 100 # End after 100 steps
        
        info = {
            'departed': departed,
            'incoming': incoming_vehicles,
            'total_queue': np.sum(self.queues)
        }
        
        return self.get_state(), reward, done, info
