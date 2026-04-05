#!/usr/bin/env python3
"""
Adaptive Traffic Signal Timing Algorithm

This module implements an adaptive traffic signal controller that adjusts
green light durations based on vehicle counts and waiting times, with
configurable minimum and maximum green light durations.
"""

import numpy as np
import time
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TrafficSignalState:
    """Represents the current state of traffic signals."""
    current_phase: int
    time_in_phase: float
    phase_start_time: float
    green_times: np.ndarray  # Green time for each phase
    waiting_times: np.ndarray  # Waiting time for each lane
    vehicle_counts: np.ndarray  # Current vehicle count for each lane

class AdaptiveTrafficController:
    """
    Adaptive traffic signal timing controller using vehicle count and waiting time.

    Features:
    - Dynamic green light duration calculation
    - Waiting time accumulation and prioritization
    - Configurable min/max green times
    - Multiple phases support (4-phase intersection)
    - Emergency vehicle prioritization
    """

    def __init__(self,
                 num_phases: int = 4,
                 min_green_time: float = 10.0,
                 max_green_time: float = 60.0,
                 base_green_time: float = 20.0,
                 count_factor: float = 2.0,
                 wait_factor: float = 1.5,
                 yellow_time: float = 3.0,
                 all_red_time: float = 2.0):
        """
        Initialize the adaptive traffic controller.

        Args:
            num_phases: Number of signal phases (typically 4 for intersection)
            min_green_time: Minimum green light duration (seconds)
            max_green_time: Maximum green light duration (seconds)
            base_green_time: Base green time before adjustments
            count_factor: Multiplier for vehicle count in green time calculation
            wait_factor: Multiplier for waiting time in green time calculation
            yellow_time: Yellow light duration (seconds)
            all_red_time: All-red clearance time (seconds)
        """
        self.num_phases = num_phases
        self.min_green_time = min_green_time
        self.max_green_time = max_green_time
        self.base_green_time = base_green_time
        self.count_factor = count_factor
        self.wait_factor = wait_factor
        self.yellow_time = yellow_time
        self.all_red_time = all_red_time

        # Initialize state
        self.state = TrafficSignalState(
            current_phase=0,
            time_in_phase=0.0,
            phase_start_time=time.time(),
            green_times=np.full(num_phases, base_green_time),
            waiting_times=np.zeros(num_phases),
            vehicle_counts=np.zeros(num_phases)
        )

        # Phase transition times
        self.phase_end_time = time.time() + base_green_time

        # Emergency vehicle override
        self.emergency_override = False
        self.emergency_phase = None

        logger.info(f"Initialized AdaptiveTrafficController with {num_phases} phases")
        logger.info(f"Green time range: {min_green_time}-{max_green_time}s")

    def update_vehicle_counts(self, vehicle_counts: np.ndarray):
        """
        Update vehicle counts for all lanes/phases.

        Args:
            vehicle_counts: Array of vehicle counts for each phase
        """
        if len(vehicle_counts) != self.num_phases:
            logger.warning(f"Vehicle counts length {len(vehicle_counts)} != num_phases {self.num_phases}")
            return

        self.state.vehicle_counts = np.array(vehicle_counts, dtype=float)
        logger.debug(f"Updated vehicle counts: {self.state.vehicle_counts}")

    def update_waiting_times(self, dt: float):
        """
        Update waiting times for lanes not currently green.

        Args:
            dt: Time delta since last update
        """
        for phase in range(self.num_phases):
            if phase != self.state.current_phase:
                self.state.waiting_times[phase] += dt

        logger.debug(f"Updated waiting times: {self.state.waiting_times}")

    def calculate_green_times(self) -> np.ndarray:
        """
        Calculate optimal green times for all phases based on current conditions.

        Returns:
            Array of calculated green times for each phase
        """
        green_times = np.zeros(self.num_phases)

        for phase in range(self.num_phases):
            # Base calculation: vehicle count + waiting time penalty
            count_contribution = self.count_factor * self.state.vehicle_counts[phase]
            wait_contribution = self.wait_factor * self.state.waiting_times[phase]

            calculated_time = self.base_green_time + count_contribution + wait_contribution

            # Apply min/max constraints
            green_times[phase] = np.clip(calculated_time,
                                       self.min_green_time,
                                       self.max_green_time)

        self.state.green_times = green_times
        logger.debug(f"Calculated green times: {green_times}")
        return green_times

    def should_switch_phase(self) -> bool:
        """
        Determine if it's time to switch to the next phase.

        Returns:
            True if phase should switch
        """
        current_time = time.time()

        # Check emergency override
        if self.emergency_override and self.emergency_phase is not None:
            if self.state.current_phase != self.emergency_phase:
                return True

        # Check if current phase time has expired
        if current_time >= self.phase_end_time:
            return True

        # Check if another phase has higher priority (much higher demand)
        current_green = self.state.green_times[self.state.current_phase]
        max_other_green = np.max(self.state.green_times[np.arange(self.num_phases) != self.state.current_phase])

        # Switch if another phase needs 1.5x more time and has been waiting
        if (max_other_green > current_green * 1.5 and
            np.max(self.state.waiting_times[np.arange(self.num_phases) != self.state.current_phase]) > 10.0):
            return True

        return False

    def switch_to_next_phase(self) -> int:
        """
        Switch to the next phase and return the new phase.

        Returns:
            New current phase
        """
        # Handle emergency override
        if self.emergency_override and self.emergency_phase is not None:
            new_phase = self.emergency_phase
            self.emergency_override = False
            self.emergency_phase = None
        else:
            # Select phase with highest calculated green time
            new_phase = np.argmax(self.state.green_times)

        # Reset waiting time for the new green phase
        self.state.waiting_times[new_phase] = 0

        # Update state
        self.state.current_phase = new_phase
        self.state.time_in_phase = 0
        self.state.phase_start_time = time.time()

        # Set new phase end time (green time + yellow + all-red)
        self.phase_end_time = (self.state.phase_start_time +
                             self.state.green_times[new_phase] +
                             self.yellow_time +
                             self.all_red_time)

        logger.info(f"Switched to phase {new_phase}, green time: {self.state.green_times[new_phase]:.1f}s")
        return new_phase

    def set_emergency_override(self, phase: int):
        """
        Set emergency vehicle override for a specific phase.

        Args:
            phase: Phase to prioritize for emergency vehicle
        """
        if 0 <= phase < self.num_phases:
            self.emergency_override = True
            self.emergency_phase = phase
            logger.info(f"Emergency override set for phase {phase}")
        else:
            logger.warning(f"Invalid emergency phase: {phase}")

    def update(self, vehicle_counts: np.ndarray, dt: float) -> Dict[str, Any]:
        """
        Main update function called each timestep.

        Args:
            vehicle_counts: Current vehicle counts for each phase
            dt: Time delta since last update

        Returns:
            Dictionary with current state information
        """
        # Update vehicle counts and waiting times
        self.update_vehicle_counts(vehicle_counts)
        self.update_waiting_times(dt)

        # Update time in current phase
        self.state.time_in_phase += dt

        # Recalculate green times
        self.calculate_green_times()

        # Check if phase should switch
        phase_switched = False
        if self.should_switch_phase():
            old_phase = self.state.current_phase
            new_phase = self.switch_to_next_phase()
            phase_switched = True

        # Determine current signal state
        current_time = time.time()
        time_remaining = max(0, self.phase_end_time - current_time)

        if time_remaining > (self.yellow_time + self.all_red_time):
            signal_state = "green"
        elif time_remaining > self.all_red_time:
            signal_state = "yellow"
        else:
            signal_state = "red"

        return {
            'current_phase': self.state.current_phase,
            'signal_state': signal_state,
            'time_in_phase': self.state.time_in_phase,
            'time_remaining': time_remaining,
            'green_times': self.state.green_times.tolist(),
            'waiting_times': self.state.waiting_times.tolist(),
            'vehicle_counts': self.state.vehicle_counts.tolist(),
            'phase_switched': phase_switched,
            'emergency_override': self.emergency_override
        }

    def get_state(self) -> Dict[str, Any]:
        """
        Get current controller state.

        Returns:
            Dictionary with current state
        """
        return {
            'current_phase': self.state.current_phase,
            'time_in_phase': self.state.time_in_phase,
            'green_times': self.state.green_times.tolist(),
            'waiting_times': self.state.waiting_times.tolist(),
            'vehicle_counts': self.state.vehicle_counts.tolist(),
            'emergency_override': self.emergency_override,
            'emergency_phase': self.emergency_phase
        }

    def reset(self):
        """
        Reset the controller to initial state.
        """
        self.state = TrafficSignalState(
            current_phase=0,
            time_in_phase=0.0,
            phase_start_time=time.time(),
            green_times=np.full(self.num_phases, self.base_green_time),
            waiting_times=np.zeros(self.num_phases),
            vehicle_counts=np.zeros(self.num_phases)
        )
        self.phase_end_time = time.time() + self.base_green_time
        self.emergency_override = False
        self.emergency_phase = None
        logger.info("Controller reset to initial state")


# Example usage and testing
def simulate_adaptive_control():
    """
    Simulate the adaptive traffic controller with sample data.
    """
    controller = AdaptiveTrafficController(
        num_phases=4,
        min_green_time=10,
        max_green_time=60,
        base_green_time=20,
        count_factor=1.5,
        wait_factor=1.0
    )

    # Simulate 5 minutes of traffic
    simulation_time = 300  # 5 minutes
    dt = 1.0  # 1 second steps

    print("Starting adaptive traffic control simulation...")
    print("Phase | Green Time | Vehicles | Waiting | Signal")
    print("-" * 50)

    for t in range(0, simulation_time, int(dt)):
        # Generate sample vehicle counts (simulate varying traffic)
        vehicle_counts = np.array([
            5 + 3 * np.sin(t / 30),  # Phase 0: moderate traffic
            8 + 5 * np.sin(t / 20 + np.pi/2),  # Phase 1: higher traffic
            3 + 2 * np.sin(t / 40 + np.pi),  # Phase 2: low traffic
            6 + 4 * np.sin(t / 25 + 3*np.pi/2)  # Phase 3: medium traffic
        ])
        vehicle_counts = np.maximum(0, vehicle_counts.astype(int))

        # Update controller
        state = controller.update(vehicle_counts, dt)

        # Print status every 10 seconds
        if t % 10 == 0:
            print(f"{state['current_phase']:5d} | "
                  f"{state['green_times'][state['current_phase']]:10.1f} | "
                  f"{vehicle_counts[state['current_phase']]:8d} | "
                  f"{state['waiting_times'][state['current_phase']]:7.1f} | "
                  f"{state['signal_state']:6s}")

    print("\nSimulation completed.")
    final_stats = controller.get_state()
    print(f"Final phase: {final_stats['current_phase']}")
    print(f"Total waiting times: {final_stats['waiting_times']}")


if __name__ == "__main__":
    simulate_adaptive_control()