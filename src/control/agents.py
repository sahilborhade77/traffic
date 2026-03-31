import numpy as np
import random
import logging

logger = logging.getLogger(__name__)

class RuleBasedAgent:
    """
    Baseline Agent: Longest-Queue-First (LQF).
    Selects the lane with the highest wait count.
    """
    def __init__(self, action_space):
        """
        :param action_space: Number of available signal phases/lanes
        """
        self.action_space = action_space

    def get_action(self, state):
        """
        Input state: [queue0, queue1, ..., active_phase]
        We only look at the first 'action_space' elements which are the queue lengths.
        """
        queues = state[:self.action_space]
        # Return the index of the largest queue
        return np.argmax(queues)

class QLearningAgent:
    """
    Placeholder for Future RL Training (Q-Learning / DQN).
    Initializes a basic Q-table.
    """
    def __init__(self, action_space, alpha=0.1, gamma=0.9, epsilon=0.1):
        self.action_space = action_space
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        # A simple state-action table: {state_tuple: [q_values_for_each_action]}
        self.q_table = {}

    def get_action(self, state):
        """Epsilon-greedy action selection."""
        state_tuple = tuple(map(int, state))
        
        # 1. Explore
        if random.uniform(0, 1) < self.epsilon:
            return random.choice(range(self.action_space))
        
        # 2. Exploit (or init Q-values if unseen)
        if state_tuple not in self.q_table:
            self.q_table[state_tuple] = np.zeros(self.action_space)
            
        return np.argmax(self.q_table[state_tuple])

    def update(self, state, action, reward, next_state):
        """Bellman Equation Update."""
        s = tuple(map(int, state))
        s_next = tuple(map(int, next_state))
        
        if s_next not in self.q_table:
            self.q_table[s_next] = np.zeros(self.action_space)
            
        old_value = self.q_table[s][action]
        next_max = np.max(self.q_table[s_next])
        
        # Update rule: Q(s, a) = Q(s, a) + alpha * (reward + gamma*max Q(s', a') - Q(s, a))
        new_value = old_value + self.alpha * (reward + self.gamma * next_max - old_value)
        self.q_table[s][action] = new_value
