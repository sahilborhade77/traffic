import cv2
import pandas as pd
import numpy as np
import time
import os
import json
import logging
from .detector import VehicleDetector

logger = logging.getLogger(__name__)

class TrafficVideoProcessor:
    """
    Enhanced Video Analysis with Tracking and Lane-wise Counting.
    """
    def __init__(self, video_path, detector, lane_definitions=None):
        """
        :param video_path: Input video source
        :param detector: Instance of VehicleDetector class
        :param lane_definitions: Dict of lane names and their polygon corners (relative coordinates 0.0-1.0)
        """
        self.video_path = video_path
        self.detector = detector
        self.cap = cv2.VideoCapture(video_path)
        
        if not self.cap.isOpened():
            logger.error(f"Error opening video {video_path}")
            raise FileNotFoundError(f"Could not open {video_path}")
        
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        # Lane Setup - default to two side-by-side lanes if none provided
        if lane_definitions is None:
            lane_definitions = {
                'Left Lane': [(0.1, 0.4), (0.45, 0.4), (0.45, 0.95), (0.1, 0.95)],
                'Right Lane': [(0.55, 0.4), (0.9, 0.4), (0.9, 0.95), (0.55, 0.95)]
            }
        
        # Scale lane definitions to pixel coordinates
        self.lanes = {}
        for name, pts in lane_definitions.items():
            pixels = np.array([(int(x * self.width), int(y * self.height)) for x, y in pts], np.int32)
            self.lanes[name] = pixels

        # Results & Tracking State
        self.lane_counts = {lane: {'car': 0, 'motorcycle': 0, 'bus': 0, 'truck': 0} for lane in self.lanes}
        self.counted_ids = {lane: set() for lane in self.lanes}
        self.traffic_data = []

    def process(self, output_path=None, show=True):
        """
        Run detection, tracking, and lane counting loop.
        """
        frame_id = 0
        writer = None
        
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(output_path, fourcc, self.fps, (self.width, self.height))

        try:
            while self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                start_time = time.time()
                frame_id += 1
                
                # 1. Track vehicles
                detections = self.detector.track(frame)
                
                # 2. Logic: Lane Assignment & Counting
                current_lane_density = self._update_lane_counts(detections)
                
                # 3. Draw UI Components
                frame = self._draw_lanes(frame)
                frame = self.detector.draw_detections(frame, detections)
                frame = self._draw_dashboard(frame, current_lane_density)
                
                # 4. Save results
                data_entry = self._prepare_data_entry(frame_id, current_lane_density)
                self.traffic_data.append(data_entry)
                
                if writer:
                    writer.write(frame)
                
                if show:
                    cv2.imshow('Smart AI Traffic - Multi-Lane Tracking', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                if frame_id % 30 == 0:
                    logger.info(f"Processed {frame_id} frames. IDs in memory: {len(detections)}")

        finally:
            self.cap.release()
            if writer:
                writer.release()
            if show:
                cv2.destroyAllWindows()

    def _update_lane_counts(self, detections):
        """
        Checks each detection's centroid against lane polygons.
        Returns the current per-lane density (number of vehicles IN the lane right now).
        Also updates persistent cumulative counts for unique IDs.
        """
        current_density = {lane: 0 for lane in self.lanes}
        
        for det in detections:
            centroid = det['centroid']
            track_id = det['track_id']
            label = det['label']
            
            for lane_name, polygon in self.lanes.items():
                # Check if centroid is inside the polygon
                is_inside = cv2.pointPolygonTest(polygon, (float(centroid[0]), float(centroid[1])), False) >= 0
                
                if is_inside:
                    current_density[lane_name] += 1
                    
                    # Avoid double counting: Add unique IDs to lane's cumulative list
                    if track_id not in self.counted_ids[lane_name]:
                        self.counted_ids[lane_name].add(track_id)
                        if label in self.lane_counts[lane_name]:
                            self.lane_counts[lane_name][label] += 1
        
        return current_density

    def _draw_lanes(self, frame):
        """
        Visualizes the lane boundaries on the frame.
        """
        for name, polygon in self.lanes.items():
            cv2.polylines(frame, [polygon], True, (255, 0, 0), 2)
            cv2.putText(frame, name, (polygon[0][0], polygon[0][1] - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        return frame

    def _draw_dashboard(self, frame, density):
        """
        Draw a scoreboard overlay.
        """
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (self.width - 10, 100), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        # Display Lane Totals
        y_pos = 40
        for name, counts in self.lane_counts.items():
            total = sum(counts.values())
            current = density[name]
            text = f"{name} -> Total: {total} vehicles | In-Lane: {current}"
            cv2.putText(frame, text, (30, y_pos), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_pos += 30
            
        return frame

    def _prepare_data_entry(self, frame_id, density):
        """
        Formats data for output file.
        """
        entry = {
            'frame_id': frame_id,
            'timestamp': time.time(),
            'lane_data': {}
        }
        for lane in self.lanes:
            entry['lane_data'][lane] = {
                'current_density': density[lane],
                'cumulative_stats': self.lane_counts[lane]
            }
        return entry

    def save_results(self, csv_file='traffic_analytics.csv', json_file='traffic_analytics.json'):
        """
        Save the entire processing log to structured formats.
        """
        if not self.traffic_data:
            return
            
        # Save JSON
        with open(json_file, 'w') as f:
            json.dump(self.traffic_data, f, indent=4)
        
        # Save flattened CSV for data science
        rows = []
        for entry in self.traffic_data:
            row = {'frame_id': entry['frame_id']}
            for lane, stats in entry['lane_data'].items():
                row[f'{lane}_density'] = stats['current_density']
                for cls, count in stats['cumulative_stats'].items():
                    row[f'{lane}_{cls}_total'] = count
            rows.append(row)
            
        pd.DataFrame(rows).to_csv(csv_file, index=False)
        logger.info(f"Analysis saved to {csv_file} and {json_file}")
