import numpy as np
import time
import torch
import logging

logger = logging.getLogger(__name__)

class IncidentDetector:
    """
    Advanced AI Monitor for accidents, breakdowns, and traffic disruptions.
    """
    def __init__(self, intersection_center=(540, 960)):
        self.stopped_vehicle_threshold = 30  # seconds
        self.center_of_intersection = intersection_center
        self.active_incidents = []
        
    def detect_accident(self, vehicle_trajectories, frame_id, fps=30):
        """
        Main monitor loop for incident detection.
        :param vehicle_trajectories: Dict {track_id: list of (x,y) points}
        """
        incidents = []
        
        # 1. Detect Abnormal Stoppages
        # (Vehicles stopped where they definitely shouldn't be)
        for track_id, trajectory in vehicle_trajectories.items():
            if self.is_vehicle_stopped_abnormally(trajectory, fps):
                incident = {
                    'type': 'STOPPED_VEHICLE',
                    'location': trajectory[-1],
                    'track_id': track_id,
                    'severity': 'MEDIUM',
                    'timestamp': time.time()
                }
                incidents.append(incident)
                self.alert_authorities(incident)
                
        return incidents
    
    def is_vehicle_stopped_abnormally(self, trajectory, fps):
        """
        Determines if a vehicle has stopped in a high-risk area (e.g. the intersection center).
        """
        wait_frames = int(3 * fps) # Look at the last 3 seconds
        if len(trajectory) < wait_frames:
            return False
        
        recent = trajectory[-wait_frames:]
        # Calculate movement variance (how much the car is 'wiggling' in pixels)
        x_variance = np.var([p[0] for p in recent])
        y_variance = np.var([p[1] for p in recent])
        
        # If variance is very low (< 5 pixels), the vehicle is stationary
        if x_variance < 5 and y_variance < 5:
            last_pos = recent[-1]
            
            # Check if this stop is at the CENTER (the middle of the box)
            # which usually means an accident or breakdown, not a red light.
            distance_to_center = np.sqrt(
                (last_pos[0] - self.center_of_intersection[0])**2 +
                (last_pos[1] - self.center_of_intersection[1])**2
            )
            
            # If stopped within 150px of center, it's an abnormal stop!
            if distance_to_center < 150:
                return True
        
        return False
    
    def alert_authorities(self, incident):
        """
        Sends an immediate incident report to the dashboard.
        """
        msg = f"🚨 INCIDENT DETECTED! Type: [{incident['type']}] | ID: {incident['track_id']} | Severity: {incident['severity']}"
        logger.error(msg)
        
        # Additional metadata for the authorities
        alert_payload = {
            'timestamp': time.ctime(),
            'incident_type': incident['type'],
            'severity': incident['severity'],
            'location_pixels': incident['location'],
            'camera_id': 'INTERSECTION_A_01'
        }
        
        # You can later extend this to call a real SMS or Email API
        return alert_payload
