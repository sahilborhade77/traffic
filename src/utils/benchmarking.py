import pandas as pd
import numpy as np
import time
import logging
from src.control.environment import TrafficSignalEnv

logger = logging.getLogger(__name__)

class TrafficBenchmarker:
    """
    Compares AI (PPO) against traditional traffic control baselines.
    """
    def __init__(self, env):
        self.env = env
        self.results = []

    def run_fixed_timing(self, interval=30):
        """Baseline 1: Standard cycle-based timing (no AI)."""
        logger.info("Benchmarking FIXED-TIMING (30s cycle)...")
        obs, _ = self.env.reset()
        total_reward = 0
        current_phase = 0
        
        for step in range(self.env.max_steps):
            if step % interval == 0:
                current_phase = (current_phase + 1) % 4
            
            obs, reward, terminated, _, _ = self.env.step(current_phase)
            total_reward += reward
            if terminated: break
            
        self.results.append({'controller': 'Fixed-Timing', 'total_reward': total_reward})

    def run_rule_based(self, threshold=15):
        """Baseline 2: Sensor-based logic (switch if busy)."""
        logger.info("Benchmarking RULE-BASED (Density-triggered)...")
        obs, _ = self.env.reset()
        total_reward = 0
        current_phase = 0

        for step in range(self.env.max_steps):
            densities = obs[:4]
            # Switch to the lane with the highest density if it exceeds threshold
            max_lane = np.argmax(densities)
            if densities[max_lane] > threshold:
                current_phase = max_lane
                
            obs, reward, terminated, _, _ = self.env.step(int(current_phase))
            total_reward += reward
            if terminated: break

        self.results.append({'controller': 'Rule-Based', 'total_reward': total_reward})

    def run_ai_ppo(self, model):
        """Benchmark: Your trained PPO AI."""
        logger.info("Benchmarking RL-PPO (AI optimized)...")
        obs, _ = self.env.reset()
        total_reward = 0
        
        for step in range(self.env.max_steps):
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, _, _ = self.env.step(action)
            total_reward += reward
            if terminated: break
            
        self.results.append({'controller': 'AI-PPO', 'total_reward': total_reward})

    def save_benchmark(self, output_path="data/benchmark_results.csv"):
        df = pd.DataFrame(self.results)
        df.to_csv(output_path, index=False)
        logger.info(f"Benchmarking complete! Results saved to {output_path}")
        return df
