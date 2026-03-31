import os
import argparse
import pandas as pd
import numpy as np
import logging
import torch
from src.control.environment import TrafficSignalEnv
from src.control.agents import RuleBasedAgent, DQNAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_training(env, agent, num_episodes=50):
    """
    Train the DQN Agent by interacting with the environment.
    """
    logger.info("Training DQN Agent...")
    history = []
    
    for episode in range(num_episodes):
        state = env.reset()
        total_reward = 0
        done = False
        step = 0
        
        while not done:
            # 1. Action
            action = agent.get_action(state, train=True)
            
            # 2. Step
            next_state, reward, done, info = env.step(action)
            
            # 3. Memory & Update
            agent.store_experience(state, action, reward, next_state, done)
            agent.train(batch_size=32)
            
            state = next_state
            total_reward += reward
            step += 1
            
        history.append({'episode': episode+1, 'total_reward': total_reward, 'epsilon': agent.epsilon})
        if (episode+1) % 10 == 0:
            logger.info(f"Episode {episode+1} -> Reward: {total_reward:.2f} | Epsilon: {agent.epsilon:.2f}")
            
    return pd.DataFrame(history)

def run_evaluation(env, agent, mode_name="DQN"):
    """
    Evaluate an agent without training (exploration = 0).
    """
    logger.info(f"Evaluating {mode_name} Agent...")
    state = env.reset()
    total_reward = 0
    done = False
    stats = []
    
    while not done:
        # Use get_action(state, train=False) for testing
        if hasattr(agent, 'get_action'): 
            # Check if it takes "train" parameter (DQN) or not (RuleBased)
            try:
                action = agent.get_action(state, train=False)
            except TypeError:
                action = agent.get_action(state)
        
        next_state, reward, done, info = env.step(action)
        
        stats.append({
            'mode': mode_name,
            'step': env.step_count,
            'reward': reward,
            'total_queue': info['total_queue'],
            'green_lane': action
        })
        
        state = next_state
        total_reward += reward
        
    logger.info(f"{mode_name} Evaluation Score: {total_reward:.2f}")
    return pd.DataFrame(stats)

def main():
    parser = argparse.ArgumentParser(description="Module 2: DQN Adaptive Signal Control")
    parser.add_argument("--train", action="store_true", help="Perform training before evaluation")
    parser.add_argument("--episodes", type=int, default=100, help="Number of training episodes")
    parser.add_argument("--save", default="models/dqn_traffic.pth", help="Path to save trained model")
    
    args = parser.parse_args()
    os.makedirs('models', exist_ok=True)
    os.makedirs('data', exist_ok=True)

    env = TrafficSignalEnv(num_lanes=4)
    state_dim = env.get_state().shape[0]
    action_dim = env.num_lanes
    
    # 1. DQN Agent Setup
    dqn_agent = DQNAgent(state_dim, action_dim)
    
    # 2. Rule-Based Agent Baseline
    baseline_agent = RuleBasedAgent(action_space=4)

    # 3. Training Loop
    if args.train:
        train_stats = run_training(env, dqn_agent, num_episodes=args.episodes)
        dqn_agent.save(args.save)
        train_stats.to_csv("data/training_log.csv")
        logger.info("Training complete. Stats saved to data/training_log.csv")
    
    # 4. Comparative Evaluation
    logger.info("-" * 30)
    logger.info("COMPARATIVE EVALUATION")
    logger.info("-" * 30)
    
    # Eval Baseline
    baseline_eval = run_evaluation(env, baseline_agent, mode_name="Rule-Based (LQF)")
    
    # Eval DQN (loading if not just trained)
    if not args.train and os.path.exists(args.save):
        dqn_agent.load(args.save)
    dqn_eval = run_evaluation(env, dqn_agent, mode_name="DQN-AI")
    
    # 5. Output Summary
    comparison = pd.concat([baseline_eval, dqn_eval])
    comparison.to_csv("data/control_performance.csv", index=False)
    
    logger.info("Evaluation results saved to data/control_performance.csv")
    logger.info("Open this file to compare 'total_queue' and 'reward' between agents.")

if __name__ == "__main__":
    main()
