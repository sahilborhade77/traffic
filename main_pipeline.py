import os
import cv2
import torch
import numpy as np
import logging
from collections import deque

from src.utils.config import CONFIG
from src.detection.vehicle_detector import VehicleDetector
from src.control.environment import TrafficSignalEnv
from src.control.dqn_agent import DQNAgent
from src.prediction.lstm_model import TrafficFlowPredictor

# Setup global logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TrafficPipeline")

class SmartTrafficPipeline:
    """
    Connected Industrial Workflow: Vision -> Prediction -> Control.
    """
    def __init__(self, dqn_path=None, lstm_path=None):
        self.video_source = CONFIG.get('paths', {}).get('input_video', 'data/traffic_sample.mp4')
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"Connected Pipeline initialized. Acceleration: {self.device.upper()}")
        
        try:
            # 1. Vision Module
            logger.info("Initializing Module 1: Vision (YOLOv8)...")
            self.detector = VehicleDetector(model_path=CONFIG['paths']['model_yolo'])
            self.cap = cv2.VideoCapture(self.video_source)
            if not self.cap.isOpened():
                raise ConnectionError(f"Could not open video source: {self.video_source}")
            
            # 2. Prediction Module (LSTM)
            logger.info("Initializing Module 3: Prediction (LSTM)...")
            self.history = deque(maxlen=CONFIG['prediction']['history_window'])
            self.lstm = TrafficFlowPredictor()
            if lstm_path and os.path.exists(lstm_path):
                self.lstm.load_state_dict(torch.load(lstm_path))
                self.lstm.eval()
                logger.info("LSTM Model loaded from checkpoint.")
            else:
                logger.warning("No pre-trained LSTM found, using initialized weights.")
            
            # 3. Control Module (DQN)
            logger.info("Initializing Module 2: Control Hub...")
            self.env = TrafficSignalEnv(num_lanes=4)
            # Initialize with dummy DQN or rule-based logic
            self.current_action = 0
            
            logger.info("Pipeline Ready for Execution.")
        except Exception as e:
            logger.critical(f"Failed to initialize pipeline! Error: {e}")
            raise

    def run(self):
        """Unified traffic intelligence loop with crash protection."""
        logger.info(f"Starting Traffic Pipeline on: {self.video_source}")
        frame_id = 0
        
        try:
            while self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    logger.info("End of video stream reached.")
                    break
                
                frame_id += 1
                
                # --- STEP 1: VISION (Detection) ---
                detections = self.detector.track(frame)
                counts = self._get_counts(detections)
                total_current = sum(counts.values())
                
                # --- STEP 2: PREDICTION (Forecasting) ---
                self.history.append(total_current)
                forecast = 0.0
                if len(self.history) == CONFIG['prediction']['history_window']:
                    # Simple prediction visualization logic
                    forecast = np.mean(list(self.history)) * 1.1 # Dummy prediction for demo
                
                # --- STEP 3: CONTROL (Decision) ---
                # Simple rule-based logic for demo (switching every 100 frames)
                if frame_id % 100 == 0:
                    self.current_action = (self.current_action + 1) % 4
                
                # --- STEP 4: VISUALIZATION & LOGGING ---
                if frame_id % 5 == 0: 
                    self.detector.draw_detections(frame, detections)
                    self._draw_status(frame, counts, forecast, self.current_action)
                    cv2.imshow('Smart AI Traffic - Phase 5 Hub', frame)
                
                if frame_id % 60 == 0:
                    logger.info(f"Frame {frame_id} | Live: {total_current} | Forecast: {forecast:.1f} | Signal: Lane {self.current_action}")
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except KeyboardInterrupt:
            logger.info("Traffic Intelligence manually stopped.")
        except Exception as e:
            logger.error(f"Runtime Exception in Pipeline Loop: {e}")
        finally:
            self.cap.release()
            cv2.destroyAllWindows()
            logger.info("Pipeline Workflow finalized and resources released.")

    def _get_counts(self, detections):
        """Map detection labels to counts."""
        counts = {'car': 0, 'motorcycle': 0, 'bus': 0, 'truck': 0}
        for det in detections:
            label = det.get('label', 'car')
            if label in counts:
                counts[label] += 1
        return counts

    def _draw_status(self, frame, counts, forecast, action):
        """Draw unified pipeline status overlay."""
        h, w, _ = frame.shape
        cv2.rectangle(frame, (0, 0), (w, 60), (0, 0, 0), -1)
        status_text = f"LIVE: {sum(counts.values())} | FCST: {forecast:.1f} | SIGNAL: Lane {action}"
        cv2.putText(frame, status_text, (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

if __name__ == "__main__":
    # Launch the cleaned, professional pipeline
    pipeline = SmartTrafficPipeline()
    pipeline.run()
