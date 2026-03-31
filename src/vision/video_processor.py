import cv2
import pandas as pd
import numpy as np
import time
import os
import json
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
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

    def apply_perspective_transform(self, frame, roi_points):
        """
        Transform to bird's eye view. 
        ROI points should be 4 corners (top-left, top-right, bottom-right, bottom-left)
        """
        width, height = 800, 800
        src_pts = np.float32(roi_points)
        dst_pts = np.float32([[0, 0], [width, 0], [width, height], [0, height]])
        
        matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped = cv2.warpPerspective(frame, matrix, (width, height))
        return warped, matrix

    def process(self, output_path=None, show=True, use_perspective=False, roi_points=None):
        """
        Run detection, tracking, and lane counting loop.
        :param use_perspective: If True, warps the road area for better detection
        :param roi_points: The 4 points of the road to warp (only if use_perspective is True)
        """
        frame_id = 0
        writer = None
        
        # Scaling adjustment if using warped view (which is 800x800)
        self.active_width = 800 if use_perspective else self.width
        self.active_height = 800 if use_perspective else self.height

        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(output_path, fourcc, self.fps, (self.active_width, self.active_height))

        try:
            while self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                # OPTIONAL: Apply Perspective Warp
                if use_perspective and roi_points:
                    frame, _ = self.apply_perspective_transform(frame, roi_points)
                
                start_time = time.time()
                frame_id += 1
                
                # 1. Track vehicles
                detections = self.detector.track(frame)
                
                # 2. Logic: Lane Assignment & Counting (uses active frame size)
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
                    cv2.imshow('Smart AI Traffic - Perspective View', frame)
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

    def _draw_dashboard(self, frame, density):
        """
        Draw a scoreboard overlay.
        """
        overlay = frame.copy()
        # Use dynamic height mapping for dashboard
        cv2.rectangle(overlay, (10, 10), (self.active_width - 10, 100), (0, 0, 0), -1)
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

class AsyncTrafficProcessor(TrafficVideoProcessor):
    """
    High-performance async processor with batch handling (non-blocking).
    Extends the base processor with asynchronous concurrency.
    """
    def __init__(self, video_path, detector, lane_definitions=None):
        super().__init__(video_path, detector, lane_definitions)
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.loop = asyncio.get_event_loop()

    async def _async_process_frame(self, frame, frame_id):
        """Processes a single frame in the thread pool."""
        # Run detection in the pool (non-blocking)
        detections = await self.loop.run_in_executor(
            self.executor,
            self.detector.track,
            frame
        )
        # Process the logic for that specific frame
        density = self._update_lane_counts(detections)
        entry = self._prepare_data_entry(frame_id, density)
        return entry

    async def run_async_pipeline(self, batch_size=30):
        """Runs the entire video in async batches."""
        logger.info(f"Starting Async Pipeline (Batch Size: {batch_size})...")
        tasks = []
        frame_id = 0
        
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break
            
            frame_id += 1
            # Create task for current frame
            task = self.loop.create_task(self._async_process_frame(frame, frame_id))
            tasks.append(task)
            
            # When we hit batch size, process all together
            if len(tasks) >= batch_size:
                batch_results = await asyncio.gather(*tasks)
                self.traffic_data.extend(batch_results)
                tasks = []
                logger.debug(f"Processed batch at frame {frame_id}")
        
        # Process remaining
        if tasks:
            batch_results = await asyncio.gather(*tasks)
            self.traffic_data.extend(batch_results)
        
        self.cap.release()
        logger.info(f"Async Pipeline complete. Processed {frame_id} frames.")
