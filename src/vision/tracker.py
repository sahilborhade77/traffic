import time
import numpy as np
import cv2
import torch
import logging
from deep_sort_realtime.deepsort_tracker import DeepSort

logger = logging.getLogger(__name__)

class EnhancedTrafficTracker:
    """
    Advanced Multi-Object Tracking with Journey Analytics.
    Uses DeepSORT for persistent IDs and handles Entry-Exit lane transitions.
    """
    def __init__(self, lanes_dict):
        # Initialize DeepSORT with parameters optimal for traffic
        self.tracker = DeepSort(
            max_age=30,           # Track lost objects for up to 30 frames
            n_init=3,             # Confirm track after 3 consecutive frames
            max_iou_distance=0.7, # Allowed overlap for ID association
            max_cosine_distance=0.2
        )
        self.lanes = lanes_dict
        self.vehicle_trajectories = {}
        self.entry_exit_info = {}
        self.completed_journeys = []

    def update_tracking(self, yolov8_results, frame):
        """
        Updates trackers with raw YOLOv8 output.
        Expects YOLO results object.
        """
        raw_detections = []
        if yolov8_results.boxes is not None:
            boxes = yolov8_results.boxes.xyxy.cpu().numpy().astype(int)
            confs = yolov8_results.boxes.conf.cpu().numpy()
            classes = yolov8_results.boxes.cls.cpu().numpy().astype(int)
            
            # Format for DeepSORT: [([x1, y1, w, h], confidence, class_id), ...]
            for box, conf, cls in zip(boxes, confs, classes):
                x1, y1, x2, y2 = box
                w, h = x2 - x1, y2 - y1
                raw_detections.append(([x1, y1, w, h], float(conf), int(cls)))

        # Update DeepSORT Tracks
        tracks = self.tracker.update_tracks(raw_detections, frame=frame)
        
        current_detections = []
        for track in tracks:
            if not track.is_confirmed():
                continue
            
            track_id = track.track_id
            ltbr = track.to_ltrb() # left, top, right, bottom
            x1, y1, x2, y2 = ltbr
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            
            # 1. Store trajectory history
            if track_id not in self.vehicle_trajectories:
                self.vehicle_trajectories[track_id] = []
            self.vehicle_trajectories[track_id].append((cx, cy))

            # 2. Analytics: Detect Lane Entry/Exit
            lane_name = self._get_lane_from_point(cx, cy)
            self._update_journey(track_id, lane_name)

            current_detections.append({
                'track_id': track_id,
                'class_id': track.get_det_class(),
                'bbox': (int(x1), int(y1), int(x2), int(y2)),
                'centroid': (int(cx), int(cy)),
                'current_lane': lane_name
            })
            
        return current_detections

    def _get_lane_from_point(self, x, y):
        """Helper to find which defined lane a point belongs to."""
        for name, polygon in self.lanes.items():
            if cv2.pointPolygonTest(polygon, (float(x), float(y)), False) >= 0:
                return name
        return "Unknown"

    def _update_journey(self, track_id, lane_name):
        """Calculates journey time and entry/exit correlation."""
        if lane_name == "Unknown":
            return

        if track_id not in self.entry_exit_info:
            # Entry detected
            self.entry_exit_info[track_id] = {
                'entry_lane': lane_name,
                'entry_time': time.time(),
                'exit_lane': None,
                'exit_time': None,
                'path': [lane_name]
            }
        else:
            journey = self.entry_exit_info[track_id]
            # Track movement across lanes
            if lane_name != journey['path'][-1]:
                journey['path'].append(lane_name)
                
                # Check for lane change (exit from original entry lane)
                if journey['exit_lane'] is None:
                    journey['exit_lane'] = lane_name
                    journey['exit_time'] = time.time()
                    duration = journey['exit_time'] - journey['entry_time']
                    
                    log_msg = f"Vehicle {track_id}: {journey['entry_lane']} → {lane_name} ({duration:.2f}s)"
                    logger.info(log_msg)
                    self.completed_journeys.append(log_msg)
