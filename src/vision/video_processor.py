import cv2
import pandas as pd
import time
import os
import logging
from .detector import VehicleDetector

logger = logging.getLogger(__name__)

class TrafficVideoProcessor:
    """
    Processes video stream for traffic analysis.
    """
    def __init__(self, video_path, detector):
        """
        :param video_path: Path to the input video file (e.g., traffic.mp4)
        :param detector: Instance of VehicleDetector class
        """
        self.video_path = video_path
        self.detector = detector
        self.cap = cv2.VideoCapture(video_path)
        
        if not self.cap.isOpened():
            logger.error(f"Error: Could not open video file {video_path}")
            raise FileNotFoundError(f"Could not open {video_path}")
        
        # Get video properties
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Results storage
        self.traffic_data = []

    def process(self, output_path=None, show=True):
        """
        Run detection and processing loop.
        :param output_path: Path to save the processed video (optional)
        :param show: Whether to show the processed video in a window
        """
        frame_id = 0
        writer = None
        
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(output_path, fourcc, self.fps, (self.width, self.height))
            logger.info(f"Saving processed video to {output_path}")

        try:
            while self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                start_time = time.time()
                frame_id += 1
                
                # 1. Detect
                detections = self.detector.detect(frame)
                
                # 2. Count by class
                counts = self._get_counts(detections)
                counts['frame_id'] = frame_id
                
                # 3. Store data for CSV
                self.traffic_data.append(counts)
                
                # 4. Draw
                frame = self.detector.draw_detections(frame, detections)
                
                # Display overlay
                self._draw_overlay(frame, counts)
                
                # 5. Save/Show
                if writer:
                    writer.write(frame)
                
                if show:
                    cv2.imshow('Smart AI Traffic - Vehicle Detection', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                fps_actual = 1 / (time.time() - start_time)
                if frame_id % 30 == 0:
                    logger.info(f"Processed Frame {frame_id} at {fps_actual:.1f} FPS")

        finally:
            self.cap.release()
            if writer:
                writer.release()
            if show:
                cv2.destroyAllWindows()
            logger.info("Processing complete.")

    def _get_counts(self, detections):
        """
        Helper to count detections by class label.
        :param detections: List of detections
        :return: Dict of class counts
        """
        counts = {'car': 0, 'motorcycle': 0, 'bus': 0, 'truck': 0}
        for det in detections:
            label = det['label']
            if label in counts:
                counts[label] += 1
        return counts

    def _draw_overlay(self, frame, counts):
        """
        Draw a HUD on the video frame showing traffic density metrics.
        """
        overlay_text = f"Cars: {counts['car']} | Buses: {counts['bus']} | Trucks: {counts['truck']} | Bikes: {counts['motorcycle']}"
        cv2.rectangle(frame, (10, 10), (550, 40), (0, 0, 0), -1)
        cv2.putText(frame, overlay_text, (20, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    def save_stats_csv(self, filename='traffic_stats.csv'):
        """
        Saves accumulated traffic data to a CSV file.
        :param filename: CSV destination
        """
        if not self.traffic_data:
            logger.warning("No traffic data collected. CSV will not be saved.")
            return
            
        df = pd.DataFrame(self.traffic_data)
        df.to_csv(filename, index=False)
        logger.info(f"Statistics saved to {filename}")
