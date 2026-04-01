import numpy as np
import torch
import logging

logger = logging.getLogger(__name__)

class AdvancedTrafficMetrics:
    """
    Measures physical traffic properties: Speed, Queue Length, and Stoppage events.
    Uses perspective geometry to map pixels to real-world meters.
    """
    def __init__(self, camera_height_meters=10, camera_angle_degrees=45, fps=30):
        self.camera_height = camera_height_meters
        self.camera_angle = np.radians(camera_angle_degrees)
        self.fps = fps
    
    def estimate_vehicle_speed(self, trajectory_points, time_delta):
        """
        Estimate speed in km/h using recent trajectory and camera calibration.
        """
        if len(trajectory_points) < 2:
            return 0
        
        # Calculate pixel distance between last two points
        p1, p2 = trajectory_points[-2], trajectory_points[-1]
        pixel_distance = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
        
        # Convert to real-world distance (meters)
        real_distance = self.pixel_to_meters(pixel_distance, p1[1])
        
        # Calculate speed (km/h)
        speed_ms = real_distance / time_delta
        speed_kmh = speed_ms * 3.6
        
        return round(speed_kmh, 2)
    
    def pixel_to_meters(self, pixel_distance, y_position):
        """
        Convert pixel distance to real-world meters.
        Approximates depth based on Y-position in the frame.
        """
        # Lower y (top of image) is further away -> scale factor is smaller
        # Higher y (bottom of image) is closer -> scale factor is larger
        scale_factor = 0.05 + (y_position / 1080) * 0.1 
        return pixel_distance * scale_factor
    
    def calculate_queue_length(self, vehicle_positions):
        """
        Calculate number of vehicles and total length of a queue in a lane.
        :param vehicle_positions: List of (x, y) centroids in a specific lane.
        """
        if not vehicle_positions:
            return {'count': 0, 'meters': 0}

        # Sort vehicles by Y position (assuming vertical lane flow for simplicity)
        sorted_vehicles = sorted(vehicle_positions, key=lambda v: v[1])
        
        queue_count = 0
        queue_length_meters = 0
        
        for i in range(len(sorted_vehicles) - 1):
            # Calculate gap between adjacent cars in the lane
            p1, p2 = sorted_vehicles[i], sorted_vehicles[i+1]
            pixel_gap = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            gap_meters = self.pixel_to_meters(pixel_gap, p1[1])
            
            # If gap is less than 10 meters, vehicles are considered "queued"
            if gap_meters < 10:
                queue_count += 1
                queue_length_meters += gap_meters
            else:
                break  # The queue has a gap, so it ends here
        
        return {
            'queue_count': queue_count + 1 if queue_count > 0 else 0,
            'queue_meters': round(queue_length_meters, 2)
        }
    
    def detect_stopped_vehicles(self, track_id, trajectory, time_window=3):
        """
        Detects if a vehicle has been stationary (potential accident/breakdown).
        """
        points_needed = int(time_window * self.fps)
        if len(trajectory) < points_needed:
            return False
        
        recent_points = trajectory[-points_needed:]
        
        # Calculate variance in position
        x_coords = [p[0] for p in recent_points]
        y_coords = [p[1] for p in recent_points]
        
        x_var = np.var(x_coords)
        y_var = np.var(y_coords)
        
        # If variance is extremely low, the vehicle hasn't moved
        if x_var < 5 and y_var < 5:
            logger.warning(f"⚠️  STALLED VEHICLE DETECTED: ID {track_id}")
            return True
        
        return False
