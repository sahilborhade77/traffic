import time
import logging

logger = logging.getLogger(__name__)

class SignalController:
    """
    Bridges the RL AI with physical/simulated traffic signals.
    Ensures safe transitions (Yellow/All-Red) and minimum/maximum green constraints.
    """
    def __init__(self, rl_controller=None):
        self.rl_controller = rl_controller
        self.current_phase = 0
        self.phase_start_time = time.time()
        
        # Phase definitions (Professional Traffic Layout)
        self.phases = {
            0: {'green_lanes': ['North', 'South'], 'red_lanes': ['East', 'West']},
            1: {'green_lanes': ['East', 'West'], 'red_lanes': ['North', 'South']},
            2: {'green_lanes': ['North'], 'red_lanes': ['South', 'East', 'West']},  # Protected turn
            3: {'green_lanes': ['West'], 'red_lanes': ['North', 'South', 'East']}
        }
        
        # Industry Standard Constraints
        self.min_green = 15    # minimum green seconds
        self.max_green = 90    # maximum green seconds
        self.yellow_time = 3   # yellow clearance seconds
        self.all_red_time = 2  # all-red safety clearance seconds
        
        # Phase 4.1: Emergency Priority Support
        self.emergency_mode = False
        self.emergency_lane_target = None
    
    def force_phase(self, phase_id):
        """Immediately forces a signal phase, bypassing AI logic (for Emergencies)."""
        if self.current_phase != phase_id:
            logger.warning(f"🚨 FORCING EMERGENCY PHASE: {phase_id}")
            self.change_phase(phase_id)

    def update_signal(self, lane_densities):
        """
        Calls the RL controller to get the best phase and updates the lights.
        :param lane_densities: Dict {lane_name: count}
        """
        current_time = time.time()
        time_in_phase = current_time - self.phase_start_time
        
        if self.rl_controller is None:
            return self.get_signal_status()

        # Get optimal phase from our RL AI Brain
        optimal_phase = self.rl_controller.get_optimal_phase(
            lane_densities,
            self.current_phase,
            time_in_phase
        )
        
        # Determine if we should change (AI request + Min Green constraint)
        if optimal_phase != self.current_phase:
            if time_in_phase >= self.min_green:
                self.change_phase(optimal_phase)
            elif time_in_phase >= self.max_green:
                # Force change if max green reached
                self.change_phase(optimal_phase)
        
        return self.get_signal_status()
    
    def change_phase(self, new_phase_id):
        """Safely transitions between phases using Yellow and All-Red buffers."""
        logger.info(f"🚦 Transitioning: Phase {self.current_phase} -> Phase {new_phase_id}")
        
        # 1. Yellow Transition (Warning)
        self.set_lights_for_transition('YELLOW')
        time.sleep(self.yellow_time)
        
        # 2. All-Red Clearance (Safety buffer for cars inside intersection)
        self.set_lights_for_transition('RED')
        time.sleep(self.all_red_time)
        
        # 3. Apply New Phase (Green)
        self.current_phase = new_phase_id
        self.phase_start_time = time.time()
        self._apply_phase_lights(new_phase_id)
        
        logger.info(f"🟢 GREEN ACTIVE: {self.phases[new_phase_id]['green_lanes']}")

    def set_lights_for_transition(self, state):
        """Intermediary state for all active lanes."""
        for lane in ['North', 'South', 'East', 'West']:
            self._set_hardware_state(lane, state)

    def _apply_phase_lights(self, phase_id):
        """Sets final Green/Red lights for the new phase."""
        config = self.phases[phase_id]
        for lane in config['green_lanes']:
            self._set_hardware_state(lane, 'GREEN')
        for lane in config['red_lanes']:
            self._set_hardware_state(lane, 'RED')

    def _set_hardware_state(self, lane, state):
        """
        INTERFACE: Place your Arduino/NEMA/Hardware code here.
        Currently logs to the console for simulation.
        """
        logger.debug(f"Signal Update | Lane: {lane} -> {state}")

    def get_signal_status(self):
        """Returns current signal state for the Dashboard UI."""
        return {
            'phase_id': self.current_phase,
            'time_in_phase': round(time.time() - self.phase_start_time, 1),
            'green_lanes': self.phases[self.current_phase]['green_lanes'],
            'red_lanes': self.phases[self.current_phase]['red_lanes']
        }
