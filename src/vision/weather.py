import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class WeatherAdaptiveSystem:
    """
    Analyzes environmental conditions (rain, fog, night) and 
    automatically adjusts camera parameters for better detection.
    """
    def __init__(self):
        self.current_conditions = 'clear'
        
    def detect_weather_conditions(self, frame):
        """
        Heuristic-based weather classification from video frame.
        """
        # Convert to grayscale for brightness and blur analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 1. Brightness check
        avg_brightness = np.mean(gray)
        
        # 2. Blur check (Laplacian Variance)
        # Low variance (blur) usually means fog, heavy rain, or a dirty lens.
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Simple Weather Logic
        if avg_brightness < 60:
            condition = 'night'
        elif blur_score < 100:
            condition = 'fog'
        elif blur_score < 250:
            condition = 'rain'
        else:
            condition = 'clear'
        
        if condition != self.current_conditions:
            logger.info(f"🌧️ Weather Update: Detected {condition.upper()} (Brightness: {avg_brightness:.1f}, Clarity: {blur_score:.1f})")
            self.current_conditions = condition
            
        return condition
    
    def apply_weather_enhancements(self, frame):
        """
        Preprocesses the frame based on current weather to improve YOLO accuracy.
        """
        condition = self.detect_weather_conditions(frame)
        
        # Adaptation Rules
        adaptations = {
            'clear': {'alpha': 1.0, 'beta': 0, 'conf': 0.25},
            'rain':  {'alpha': 1.3, 'beta': 10, 'conf': 0.18}, # Increase contrast, lower conf
            'fog':   {'alpha': 1.6, 'beta': 20, 'conf': 0.15}, # High contrast for mist
            'night': {'alpha': 1.2, 'beta': 40, 'conf': 0.20}, # Brightness boost
        }
        
        rules = adaptations.get(condition, adaptations['clear'])
        
        # Apply Brightness (beta) and Contrast (alpha) adjustments
        enhanced_frame = cv2.convertScaleAbs(frame, alpha=rules['alpha'], beta=rules['beta'])
        
        return enhanced_frame, rules['conf']

    def apply_dehazing_placeholder(self, frame):
        """Advanced dark channel prior dehazing could be added here."""
        return frame
