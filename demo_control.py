import os
import argparse
import pandas as pd
import numpy as np
import logging
from src.control.environment import TrafficSignalEnv
from src.control.agents import RuleBasedAgent, QLearningAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_simulation(env, agent, num_episodes=1, incoming_data=None):
    """
    Standard Traffic Simulation Loop.
    :param env: The Traffic Environment
    :param agent: The Signal Agent
    :param num_episodes: How many runs to perform
    :param incoming_data: Optional CSV/List of realistic arrivals
    """
    for episode in range(num_episodes):
        state = env.reset()
        total_reward = 0
        done = False
        step = 0
        
        while not done:
            # 1. Action: Get signal decision
            action = agent.get_action(state)
            
            # 2. Arriving Vehicles (Optional: use real data if available)
            arrivals = None
            if incoming_data is not None and step < len(incoming_data):
                # Use real per-lane arrival counts from data source
                arrivals = incoming_data[step]
            
            # 3. Step: Advance environment
            next_state, reward, done, info = env.step(action, incoming_vehicles=arrivals)
            
            # 4. Learning (Only if RL agent)
            if hasattr(agent, 'update'):
                agent.update(state, action, reward, next_state)
            
            state = next_state
            total_reward += reward
            step += 1
            
            if step % 20 == 0:
                logger.debug(f"Step {step} -> Total Queue: {info['total_queue']} | Current Signal: {state[-1]}")
                
        logger.info(f"Episode {episode+1} Completed -> Score (Total Reward): {total_reward:.2f}")

def main():
    parser = argparse.ArgumentParser(description="Module 2: Traffic Signal Control Demo")
    parser.add_argument("--mode", choices=["rule-based", "rl"], default="rule-based",
                        help="Select agent mode: rule-based (baseline) or rl (future)")
    parser.add_argument("--episodes", type=int, default=1,
                        help="Number of simulation episodes to run")

    args = parser.parse_args()

    # Step 1: Init Environment (4 Lanes)
    env = TrafficSignalEnv(num_lanes=4)
    
    # Step 2: Init Agent
    if args.mode == "rule-based":
        logger.info("Initializing Rule-Based Baseline (Longest-Queue-First)...")
        agent = RuleBasedAgent(action_space=4)
    else:
        logger.info("Initializing Q-Learning Agent Shell...")
        agent = QLearningAgent(action_space=4)

    # Step 3: Run Simulation
    logger.info(f"Running {args.episodes} episodes in {args.mode} mode...")
    run_simulation(env, agent, num_episodes=args.episodes)
    
    logger.info("Demo complete. You can experiment with different lane configurations now.")

if __name__ == "__main__":
    main()
