import cv2
import numpy as np
import time
import torch
import logging

logger = logging.getLogger(__name__)

class EmergencyVehicleDetector:
    """
    Scans for flashing lights (Red/Blue) to detect emergency vehicles.
    Can be expanded to include audio (siren) detection.
    """
    def __init__(self, lanes_dict=None):
        self.lanes = lanes_dict or {}
        
    def detect_emergency_visuals(self, frame):
        """
        Detects bright red and blue flashing patterns in the frame.
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Red light masks
        red_mask1 = cv2.inRange(hsv, (0, 100, 100), (10, 255, 255))
        red_mask2 = cv2.inRange(hsv, (160, 100, 100), (180, 255, 255))
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        
        # Blue light mask
        blue_mask = cv2.inRange(hsv, (100, 150, 100), (140, 255, 255))
        
        # Check density of red/blue pixels
        red_count = cv2.countNonZero(red_mask)
        blue_count = cv2.countNonZero(blue_mask)
        
        # Heuristic: Emergency lights are usually small but very bright
        if red_count > 100 and blue_count > 100:
            return True, max(red_count, blue_count) / 1000.0 # Return confidence
        
        return False, 0.0

    def find_vehicle_lane(self, frame):
        """Identifies which lane contains flashing lights."""
        # Simple implementation: check where red/blue pixels are most dense
        # This would be mapped to your defined lane polygons
        return "North" # Placeholder lane identification

class EmergencyResponseSystem:
    """
    Manages the overall response when an emergency vehicle is detected.
    Overwrites normal signal logic to create a 'Green Corridor'.
    """
    def __init__(self, signal_controller, lanes):
        self.detector = EmergencyVehicleDetector(lanes)
        self.signal_controller = signal_controller
        self.is_active = False
        
    def monitor_and_respond(self, frame):
        """
        Main monitor loop called in every frame.
        """
        detected, confidence = self.detector.detect_emergency_visuals(frame)
        
        if detected and not self.is_active:
            self.is_active = True
            logger.warning(f"🚨 EMERGENCY VEHICLE DETECTED (Confidence: {confidence:.2f})")
            
            # Determine the lane (North, South, East, West)
            lane = self.detector.find_vehicle_lane(frame)
            
            # Create the Green Corridor!
            self.signal_controller.emergency_mode = True
            
            # Force the phase that gives this lane a Green Light
            # (Assuming Phase 0 is N-S and Phase 1 is E-W)
            phase_to_force = 1 if lane in ['East', 'West'] else 0
            self.signal_controller.force_phase(phase_to_force)
            
        elif not detected and self.is_active:
            # Emergency has passed
            self.is_active = False
            self.signal_controller.emergency_mode = False
            logger.info("✅ Emergency cleared. Signal AI resuming...")
