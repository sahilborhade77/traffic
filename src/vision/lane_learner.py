import numpy as np
import cv2
import logging
from sklearn.cluster import DBSCAN

logger = logging.getLogger(__name__)

class LaneLearner:
    """
    Auto-detects lane polygons using vehicle movement history.
    """
    def __init__(self, eps=25, min_samples=30):
        self.points_buffer = []  # List of all centroids seen
        self.eps = eps           # Distance for clustering (pixels)
        self.min_samples = min_samples # Frames required to form a cluster
        self.discovered_lanes = {}

    def collect_points(self, detections):
        """Add new centroids to the learning buffer."""
        for det in detections:
            self.points_buffer.append(det['centroid'])
            
        # Limit buffer for performance (most recent 5,000 points)
        if len(self.points_buffer) > 5000:
            self.points_buffer = self.points_buffer[-5000:]

    def learn_lanes(self, frame_shape):
        """Perform clustering and build dynamic polygons."""
        if len(self.points_buffer) < self.min_samples:
            return None

        # 1. Convert to NumPy for DBSCAN
        data = np.array(self.points_buffer)
        
        # 2. Cluster dense paths
        clustering = DBSCAN(eps=self.eps, min_samples=self.min_samples).fit(data)
        labels = clustering.labels_
        
        # 3. Process clusters into Polygons
        new_rois = {}
        unique_labels = set(labels)
        
        for label in unique_labels:
            if label == -1: continue # Ignore noise
            
            # Get points for this cluster (one potential lane)
            cluster_points = data[labels == label]
            
            # Use Convex Hull to create a simple polygon for this lane corridor
            hull = cv2.convexHull(cluster_points.astype(np.int32))
            
            # 4. Identify Entry Direction
            direction = self._identify_direction(cluster_points)
            lane_id = f"AutoLane_{direction}_{label}"
            
            new_rois[lane_id] = hull.reshape(-1, 2)
            
        self.discovered_lanes = new_rois
        logger.info(f"Learned {len(new_rois)} traffic lanes from trajectories.")
        return new_rois

    def _identify_direction(self, points):
        """Detect direction based on cluster orientation."""
        x_min, y_min = np.min(points, axis=0)
        x_max, y_max = np.max(points, axis=0)
        
        if (y_max - y_min) > (x_max - x_min):
            return "Vertical"
        else:
            return "Horizontal"

    def visualize_learned_lanes(self, frame):
        """Draws discovered lane polygons with low opacity."""
        overlay = frame.copy()
        for name, polygon in self.discovered_lanes.items():
            cv2.fillPoly(overlay, [polygon], (0, 255, 0))
            cv2.putText(frame, name, tuple(polygon[0]), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        return cv2.addWeighted(overlay, 0.3, frame, 0.7, 0)
