#!/usr/bin/env python3
"""
Traffic Density Calculator

This module provides functionality to divide video frames into grid zones,
count vehicles in each zone, and generate heatmap visualizations for traffic
density analysis.
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
import logging

logger = logging.getLogger(__name__)

class TrafficDensityCalculator:
    """
    Calculates traffic density by dividing frames into grid zones and
    counting vehicles per zone with heatmap visualization.

    Features:
    - Configurable grid size (rows x columns)
    - Vehicle counting per zone based on bounding box centers
    - Heatmap visualization with color-coded density
    - Statistical analysis of traffic distribution
    """

    def __init__(self,
                 grid_rows: int = 4,
                 grid_cols: int = 4,
                 zone_names: Optional[List[str]] = None):
        """
        Initialize the traffic density calculator.

        Args:
            grid_rows: Number of rows in the grid
            grid_cols: Number of columns in the grid
            zone_names: Optional custom names for zones (must match grid size)
        """
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols

        if zone_names and len(zone_names) == grid_rows * grid_cols:
            self.zone_names = zone_names
        else:
            self.zone_names = [f"Zone_{i}_{j}" for i in range(grid_rows) for j in range(grid_cols)]

        logger.info(f"Initialized density calculator with {grid_rows}x{grid_cols} grid")

    def calculate_density(self,
                         frame: np.ndarray,
                         detections: List[Dict[str, Any]]) -> np.ndarray:
        """
        Calculate vehicle density per grid zone.

        Args:
            frame: Input video frame
            detections: List of detection dictionaries with 'bbox' key
                       bbox format: [x1, y1, x2, y2]

        Returns:
            2D numpy array with vehicle counts per zone
        """
        height, width = frame.shape[:2]
        zone_width = width // self.grid_cols
        zone_height = height // self.grid_rows

        # Initialize density map
        density_map = np.zeros((self.grid_rows, self.grid_cols), dtype=int)

        # Count vehicles in each zone
        for detection in detections:
            if 'bbox' not in detection:
                continue

            bbox = detection['bbox']
            if len(bbox) != 4:
                continue

            # Calculate center point of bounding box
            center_x = (bbox[0] + bbox[2]) / 2
            center_y = (bbox[1] + bbox[3]) / 2

            # Determine which zone the vehicle belongs to
            zone_col = int(center_x // zone_width)
            zone_row = int(center_y // zone_height)

            # Ensure indices are within bounds
            zone_col = max(0, min(zone_col, self.grid_cols - 1))
            zone_row = max(0, min(zone_row, self.grid_rows - 1))

            density_map[zone_row, zone_col] += 1

        return density_map

    def create_heatmap_overlay(self,
                              frame: np.ndarray,
                              density_map: np.ndarray,
                              alpha: float = 0.5) -> np.ndarray:
        """
        Create a heatmap overlay on the input frame.

        Args:
            frame: Input video frame
            density_map: 2D array with vehicle counts per zone
            alpha: Transparency level for heatmap overlay (0-1)

        Returns:
            Frame with heatmap overlay
        """
        height, width = frame.shape[:2]
        zone_width = width // self.grid_cols
        zone_height = height // self.grid_rows

        # Create overlay image
        overlay = frame.copy()

        # Calculate maximum density for color scaling
        max_density = np.max(density_map) if np.max(density_map) > 0 else 1

        # Draw heatmap zones
        for i in range(self.grid_rows):
            for j in range(self.grid_cols):
                density = density_map[i, j]

                # Color mapping: Green (low) -> Yellow -> Red (high)
                if density == 0:
                    color = (0, 255, 0)  # Green for no vehicles
                else:
                    # Normalize density to 0-255 range
                    intensity = min(255, int(255 * density / max_density))
                    color = (0, 255 - intensity, intensity)  # Green to red gradient

                # Draw filled rectangle for this zone
                x1 = j * zone_width
                y1 = i * zone_height
                x2 = (j + 1) * zone_width
                y2 = (i + 1) * zone_height

                cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)

                # Add density count text
                text = str(density)
                text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                text_x = x1 + 10
                text_y = y1 + 30

                # Ensure text stays within zone bounds
                text_x = min(text_x, x2 - text_size[0] - 10)
                text_y = min(text_y, y2 - 10)

                # Draw text background for better visibility
                cv2.rectangle(overlay,
                            (text_x - 5, text_y - text_size[1] - 5),
                            (text_x + text_size[0] + 5, text_y + 5),
                            (0, 0, 0), -1)

                cv2.putText(overlay, text, (text_x, text_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Blend overlay with original frame
        heatmap_frame = cv2.addWeighted(frame, 1 - alpha, overlay, alpha, 0)

        # Draw grid lines
        for i in range(1, self.grid_rows):
            y = i * zone_height
            cv2.line(heatmap_frame, (0, y), (width, y), (255, 255, 255), 1)

        for j in range(1, self.grid_cols):
            x = j * zone_width
            cv2.line(heatmap_frame, (x, 0), (x, height), (255, 255, 255), 1)

        return heatmap_frame

    def get_density_stats(self, density_map: np.ndarray) -> Dict[str, Any]:
        """
        Calculate statistical information about traffic density.

        Args:
            density_map: 2D array with vehicle counts per zone

        Returns:
            Dictionary with density statistics
        """
        total_vehicles = int(np.sum(density_map))
        avg_density = float(np.mean(density_map))
        max_density = int(np.max(density_map))
        min_density = int(np.min(density_map))

        # Find zones with highest and lowest density
        max_zone_idx = np.unravel_index(np.argmax(density_map), density_map.shape)
        min_zone_idx = np.unravel_index(np.argmin(density_map), density_map.shape)

        # Calculate density distribution
        unique, counts = np.unique(density_map, return_counts=True)
        distribution = dict(zip(unique.tolist(), counts.tolist()))

        stats = {
            'total_vehicles': total_vehicles,
            'avg_density_per_zone': avg_density,
            'max_density': max_density,
            'min_density': min_density,
            'max_density_zone': f"Zone_{max_zone_idx[0]}_{max_zone_idx[1]}",
            'min_density_zone': f"Zone_{min_zone_idx[0]}_{min_zone_idx[1]}",
            'density_distribution': distribution,
            'density_map': density_map.tolist(),
            'grid_dimensions': f"{self.grid_rows}x{self.grid_cols}"
        }

        return stats

    def process_frame(self,
                     frame: np.ndarray,
                     detections: List[Dict[str, Any]],
                     create_heatmap: bool = True) -> Dict[str, Any]:
        """
        Process a single frame: calculate density and optionally create heatmap.

        Args:
            frame: Input video frame
            detections: List of vehicle detections
            create_heatmap: Whether to generate heatmap visualization

        Returns:
            Dictionary with density statistics and optional heatmap
        """
        # Calculate density map
        density_map = self.calculate_density(frame, detections)

        # Get statistics
        stats = self.get_density_stats(density_map)

        # Create heatmap if requested
        if create_heatmap:
            heatmap_frame = self.create_heatmap_overlay(frame, density_map)
            stats['heatmap_frame'] = heatmap_frame

        return stats

    @staticmethod
    def detections_from_yolo_results(results) -> List[Dict[str, Any]]:
        """
        Convert Ultralytics YOLO results to detection format.

        Args:
            results: YOLO results object

        Returns:
            List of detection dictionaries
        """
        detections = []

        for result in results:
            if result.boxes is not None:
                boxes = result.boxes.xyxy.cpu().numpy()  # [x1, y1, x2, y2]
                classes = result.boxes.cls.cpu().numpy()  # class indices
                confs = result.boxes.conf.cpu().numpy()   # confidence scores

                for box, cls, conf in zip(boxes, classes, confs):
                    # Filter for vehicle classes (COCO: 2=car, 3=motorcycle, 5=bus, 7=truck)
                    if int(cls) in [2, 3, 5, 7]:
                        detections.append({
                            'bbox': box.tolist(),
                            'class': int(cls),
                            'confidence': float(conf)
                        })

        return detections


# Example usage and testing
def example_usage():
    """
    Example of how to use the TrafficDensityCalculator.
    """
    # Initialize calculator
    calculator = TrafficDensityCalculator(grid_rows=3, grid_cols=4)

    # Create a sample frame (for testing)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # Sample detections (normally from YOLO)
    sample_detections = [
        {'bbox': [100, 100, 150, 150]},  # Zone 0,0
        {'bbox': [200, 100, 250, 150]},  # Zone 0,1
        {'bbox': [200, 100, 250, 150]},  # Zone 0,1 (another vehicle)
        {'bbox': [500, 300, 550, 350]},  # Zone 2,3
    ]

    # Process frame
    result = calculator.process_frame(frame, sample_detections, create_heatmap=True)

    print("Density Statistics:")
    for key, value in result.items():
        if key != 'heatmap_frame':
            print(f"  {key}: {value}")

    # The heatmap_frame would be displayed or saved
    if 'heatmap_frame' in result:
        print(f"Heatmap frame shape: {result['heatmap_frame'].shape}")


if __name__ == "__main__":
    example_usage()