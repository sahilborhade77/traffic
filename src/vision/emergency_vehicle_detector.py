#!/usr/bin/env python3
"""
Emergency Vehicle Detection System

This module provides detection of emergency vehicles using visual (flashing lights)
and audio (siren) cues, with integration for traffic signal priority override.
"""

import cv2
import numpy as np
import time
import logging
from typing import Dict, List, Tuple, Optional, Any
from collections import deque
import threading

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logging.warning("librosa not available - audio siren detection disabled")

logger = logging.getLogger(__name__)

class EmergencyVehicleDetector:
    """
    Detects emergency vehicles using visual and audio cues.

    Visual Detection:
    - Identifies flashing red and blue lights
    - Tracks light patterns and frequencies
    - Determines vehicle direction/approach

    Audio Detection:
    - Analyzes siren frequency patterns
    - Detects characteristic wail/yelp/hi-lo siren sounds
    """

    def __init__(self,
                 camera_sources: List[str],
                 audio_sources: Optional[List[str]] = None,
                 detection_threshold: float = 0.7,
                 flash_frequency_min: float = 1.0,
                 flash_frequency_max: float = 3.0,
                 siren_freq_range: Tuple[float, float] = (800, 1200)):
        """
        Initialize emergency vehicle detector.

        Args:
            camera_sources: List of camera source URLs/paths
            audio_sources: Optional list of audio source devices
            detection_threshold: Confidence threshold for detection
            flash_frequency_min/max: Expected flash frequency range (Hz)
            siren_freq_range: Frequency range for siren detection (Hz)
        """
        self.camera_sources = camera_sources
        self.audio_sources = audio_sources or []
        self.detection_threshold = detection_threshold
        self.flash_freq_min = flash_frequency_min
        self.flash_freq_max = flash_frequency_max
        self.siren_freq_range = siren_freq_range

        # Visual detection parameters
        self.light_history_length = 30  # frames to track
        self.light_histories = [deque(maxlen=self.light_history_length)
                              for _ in camera_sources]

        # Color ranges for emergency lights (HSV)
        self.red_lower1 = np.array([0, 100, 100])
        self.red_upper1 = np.array([10, 255, 255])
        self.red_lower2 = np.array([160, 100, 100])
        self.red_upper2 = np.array([180, 255, 255])
        self.blue_lower = np.array([90, 100, 100])
        self.blue_upper = np.array([130, 255, 255])

        # Audio detection parameters
        self.audio_buffer_size = 1024
        self.sample_rate = 44100
        self.siren_patterns = {
            'wail': {'freq_range': (800, 1000), 'modulation': 10},
            'yelp': {'freq_range': (900, 1100), 'modulation': 20},
            'hi_lo': {'freq_range': (700, 1200), 'modulation': 5}
        }

        # Detection state
        self.emergency_detected = False
        self.detection_confidence = 0.0
        self.detected_direction = None
        self.last_detection_time = 0
        self.detection_timeout = 10.0  # seconds

        # Threading
        self.running = False
        self.detection_thread = None

        logger.info(f"Initialized EmergencyVehicleDetector with {len(camera_sources)} cameras")

    def detect_visual_emergency(self, frame: np.ndarray, camera_id: int) -> Tuple[bool, float, Optional[str]]:
        """
        Detect emergency vehicles in a video frame using visual cues.

        Args:
            frame: Input video frame
            camera_id: ID of the camera source

        Returns:
            Tuple of (detected, confidence, direction)
        """
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Create masks for red and blue lights
        red_mask1 = cv2.inRange(hsv, self.red_lower1, self.red_upper1)
        red_mask2 = cv2.inRange(hsv, self.red_lower2, self.red_upper2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)

        blue_mask = cv2.inRange(hsv, self.blue_lower, self.blue_upper)

        # Combine masks
        emergency_mask = cv2.bitwise_or(red_mask, blue_mask)

        # Morphological operations to reduce noise
        kernel = np.ones((5, 5), np.uint8)
        emergency_mask = cv2.morphologyEx(emergency_mask, cv2.MORPH_OPEN, kernel)
        emergency_mask = cv2.morphologyEx(emergency_mask, cv2.MORPH_CLOSE, kernel)

        # Find contours of potential light sources
        contours, _ = cv2.findContours(emergency_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Filter contours by size (emergency lights should be reasonably sized)
        min_area = 50
        max_area = 5000
        light_contours = [cnt for cnt in contours if min_area < cv2.contourArea(cnt) < max_area]

        # Count red and blue lights separately
        red_lights = 0
        blue_lights = 0

        for contour in light_contours:
            # Get average color in contour area
            mask = np.zeros_like(emergency_mask)
            cv2.drawContours(mask, [contour], -1, 255, -1)

            mean_color = cv2.mean(hsv, mask=mask)
            hue = mean_color[0]

            # Classify as red or blue
            if (hue < 10 or hue > 160):  # Red range
                red_lights += 1
            elif 90 <= hue <= 130:  # Blue range
                blue_lights += 1

        # Update light history for flash pattern detection
        light_count = len(light_contours)
        self.light_histories[camera_id].append(light_count)

        # Detect flashing pattern
        flash_detected = self._detect_flashing_pattern(camera_id)

        # Calculate confidence based on multiple factors
        confidence = 0.0

        # Factor 1: Presence of both red and blue lights
        if red_lights > 0 and blue_lights > 0:
            confidence += 0.4

        # Factor 2: Reasonable number of lights (emergency vehicles typically have multiple)
        if 2 <= light_count <= 8:
            confidence += 0.3

        # Factor 3: Flashing pattern detected
        if flash_detected:
            confidence += 0.3

        # Determine direction based on light positions
        direction = None
        if confidence > self.detection_threshold:
            direction = self._determine_direction(frame, light_contours)

        detected = confidence > self.detection_threshold

        return detected, confidence, direction

    def _detect_flashing_pattern(self, camera_id: int) -> bool:
        """
        Detect flashing pattern in light history.

        Args:
            camera_id: Camera ID to check

        Returns:
            True if flashing pattern detected
        """
        history = list(self.light_histories[camera_id])

        if len(history) < 10:
            return False

        # Look for alternating high/low light counts
        peaks = 0
        valleys = 0

        for i in range(1, len(history) - 1):
            if history[i] > history[i-1] and history[i] > history[i+1]:
                peaks += 1
            elif history[i] < history[i-1] and history[i] < history[i+1]:
                valleys += 1

        # Calculate flash frequency
        if peaks > 2:  # At least 3 peaks for reliable detection
            # Estimate frequency (peaks per second, assuming 30 FPS)
            estimated_freq = peaks / (len(history) / 30.0)

            if self.flash_freq_min <= estimated_freq <= self.flash_freq_max:
                return True

        return False

    def _determine_direction(self, frame: np.ndarray, light_contours) -> Optional[str]:
        """
        Determine the direction/approach of the emergency vehicle.

        Args:
            frame: Video frame
            light_contours: Detected light contours

        Returns:
            Direction string ('north', 'south', 'east', 'west') or None
        """
        if not light_contours:
            return None

        height, width = frame.shape[:2]

        # Calculate centroid of all lights
        total_x = 0
        total_y = 0
        total_area = 0

        for contour in light_contours:
            M = cv2.moments(contour)
            if M['m00'] > 0:
                cx = int(M['m10'] / M['m00'])
                cy = int(M['m01'] / M['m00'])
                area = cv2.contourArea(contour)

                total_x += cx * area
                total_y += cy * area
                total_area += area

        if total_area == 0:
            return None

        centroid_x = total_x / total_area
        centroid_y = total_y / total_area

        # Determine direction based on position in frame
        # Assuming camera view: top=North, bottom=South, left=West, right=East
        if centroid_y < height * 0.4:  # Top third
            return 'north'
        elif centroid_y > height * 0.6:  # Bottom third
            return 'south'
        elif centroid_x < width * 0.4:  # Left third
            return 'west'
        elif centroid_x > width * 0.6:  # Right third
            return 'east'
        else:
            return 'center'  # Approaching intersection

    def detect_audio_emergency(self, audio_data: np.ndarray, sample_rate: int = 44100) -> Tuple[bool, float]:
        """
        Detect emergency vehicles using audio siren analysis.

        Args:
            audio_data: Audio samples
            sample_rate: Audio sample rate

        Returns:
            Tuple of (detected, confidence)
        """
        if not LIBROSA_AVAILABLE:
            return False, 0.0

        try:
            # Compute spectrogram
            D = librosa.stft(audio_data, n_fft=2048, hop_length=512)
            S = np.abs(D)

            # Get frequency bins
            freqs = librosa.fft_frequencies(sr=sample_rate, n_fft=2048)

            # Focus on siren frequency range
            siren_mask = (freqs >= self.siren_freq_range[0]) & (freqs <= self.siren_freq_range[1])
            siren_energy = S[siren_mask]

            if siren_energy.size == 0:
                return False, 0.0

            # Calculate energy in siren frequency range
            siren_power = np.mean(siren_energy ** 2)

            # Detect modulation patterns characteristic of sirens
            confidence = 0.0

            # Check for frequency modulation (changing pitch)
            if len(audio_data) > sample_rate:  # At least 1 second
                # Simple modulation detection
                window_size = int(sample_rate * 0.1)  # 100ms windows
                modulation_score = 0

                for i in range(0, len(audio_data) - window_size, window_size // 2):
                    window = audio_data[i:i + window_size]
                    if len(window) > 0:
                        # Check for frequency changes
                        # This is a simplified approach
                        fft = np.fft.fft(window)
                        freq_changes = np.diff(np.argmax(np.abs(fft), axis=0))
                        if len(freq_changes) > 0:
                            modulation_score += np.std(freq_changes)

                if modulation_score > 0.1:  # Threshold for modulation
                    confidence += 0.5

            # Check energy threshold
            if siren_power > 0.01:  # Adjust threshold based on audio levels
                confidence += 0.5

            detected = confidence > self.detection_threshold

            return detected, confidence

        except Exception as e:
            logger.error(f"Audio detection error: {e}")
            return False, 0.0

    def process_frame(self, frame: np.ndarray, camera_id: int,
                     audio_data: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Process a single frame for emergency vehicle detection.

        Args:
            frame: Video frame
            camera_id: Camera ID
            audio_data: Optional audio data

        Returns:
            Detection results dictionary
        """
        # Visual detection
        visual_detected, visual_confidence, direction = self.detect_visual_emergency(frame, camera_id)

        # Audio detection
        audio_detected = False
        audio_confidence = 0.0

        if audio_data is not None:
            audio_detected, audio_confidence = self.detect_audio_emergency(audio_data)

        # Combine detections
        combined_confidence = max(visual_confidence, audio_confidence)
        detected = visual_detected or audio_detected

        # Update detection state
        current_time = time.time()

        if detected and combined_confidence > self.detection_threshold:
            self.emergency_detected = True
            self.detection_confidence = combined_confidence
            self.detected_direction = direction
            self.last_detection_time = current_time
        elif current_time - self.last_detection_time > self.detection_timeout:
            # Timeout - clear detection
            self.emergency_detected = False
            self.detection_confidence = 0.0
            self.detected_direction = None

        return {
            'emergency_detected': self.emergency_detected,
            'confidence': self.detection_confidence,
            'direction': self.detected_direction,
            'visual_detected': visual_detected,
            'visual_confidence': visual_confidence,
            'audio_detected': audio_detected,
            'audio_confidence': audio_confidence,
            'timestamp': current_time
        }

    def get_emergency_phase(self) -> Optional[int]:
        """
        Get the traffic phase that should be prioritized for emergency vehicle.

        Returns:
            Phase number (0-3) or None
        """
        if not self.emergency_detected or not self.detected_direction:
            return None

        # Map direction to phase (adjust based on your intersection layout)
        direction_to_phase = {
            'north': 0,  # North approach
            'south': 2,  # South approach
            'east': 1,   # East approach
            'west': 3,   # West approach
            'center': None  # At intersection, prioritize current phase
        }

        return direction_to_phase.get(self.detected_direction)

    def reset_detection(self):
        """
        Manually reset emergency detection state.
        """
        self.emergency_detected = False
        self.detection_confidence = 0.0
        self.detected_direction = None
        self.last_detection_time = 0

        # Clear light histories
        for history in self.light_histories:
            history.clear()

        logger.info("Emergency detection state reset")

    def get_detection_stats(self) -> Dict[str, Any]:
        """
        Get current detection statistics.

        Returns:
            Dictionary with detection statistics
        """
        return {
            'emergency_detected': self.emergency_detected,
            'confidence': self.detection_confidence,
            'direction': self.detected_direction,
            'last_detection_time': self.last_detection_time,
            'time_since_detection': time.time() - self.last_detection_time,
            'light_histories_length': [len(h) for h in self.light_histories]
        }


# Integration with traffic controller
def integrate_with_traffic_controller(detector: EmergencyVehicleDetector,
                                   controller: Any) -> None:
    """
    Integrate emergency detection with traffic controller.

    Args:
        detector: Emergency vehicle detector instance
        controller: Traffic controller with set_emergency_override method
    """
    def emergency_check_loop():
        """Background thread to monitor for emergency vehicles."""
        while True:
            if detector.emergency_detected:
                emergency_phase = detector.get_emergency_phase()
                if emergency_phase is not None and hasattr(controller, 'set_emergency_override'):
                    controller.set_emergency_override(emergency_phase)
                    logger.info(f"Emergency override activated for phase {emergency_phase}")

            time.sleep(0.5)  # Check every 500ms

    # Start background monitoring thread
    emergency_thread = threading.Thread(target=emergency_check_loop, daemon=True)
    emergency_thread.start()
    logger.info("Emergency vehicle monitoring started")


# Example usage and testing
def test_emergency_detection():
    """
    Test the emergency vehicle detection with sample data.
    """
    detector = EmergencyVehicleDetector(camera_sources=["dummy_camera"])

    # Create a test frame with simulated emergency lights
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # Add some red and blue light-like regions
    # Red light (top-left)
    cv2.circle(frame, (100, 100), 20, (0, 0, 255), -1)  # BGR: Red
    # Blue light (top-right)
    cv2.circle(frame, (200, 100), 20, (255, 0, 0), -1)  # BGR: Blue

    # Test detection
    results = detector.process_frame(frame, camera_id=0)

    print("Emergency Detection Test Results:")
    print(f"Emergency detected: {results['emergency_detected']}")
    print(f"Confidence: {results['confidence']:.3f}")
    print(f"Direction: {results['direction']}")
    print(f"Visual detected: {results['visual_detected']}")
    print(f"Audio detected: {results['audio_detected']}")

    # Test with multiple frames to simulate flashing
    for i in range(10):
        # Alternate light presence to simulate flashing
        test_frame = frame.copy() if i % 2 == 0 else np.zeros_like(frame)
        detector.process_frame(test_frame, camera_id=0)

    # Check final state
    final_results = detector.get_detection_stats()
    print(f"\nFinal detection state: {final_results['emergency_detected']}")
    print(f"Emergency phase: {detector.get_emergency_phase()}")


if __name__ == "__main__":
    test_emergency_detection()