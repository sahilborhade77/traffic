import os
import cv2
import torch
import numpy as np
import logging
from collections import deque
from src.utils.config import CONFIG
from src.vision.detector import VehicleDetector
from src.control.environment import TrafficSignalEnv
from src.control.dqn_agent import DQNAgent # Updated name
from src.prediction.lstm_model import TrafficFlowPredictor # Updated name

# Setup global logger
logger = logging.getLogger("TrafficPipeline")

class SmartTrafficPipeline:
    """
    Connected Industrial Workflow: Vision -> Prediction -> Control.
    """
    def __init__(self, dqn_path=None, lstm_path=None):
        self.video_source = CONFIG['paths']['input_video']
        
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
            
            # 3. Control Module (PPO/DQN)
            logger.info("Initializing Module 2: Control Hub...")
            self.env = TrafficSignalEnv(num_lanes=4)
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
                    break
                
                frame_id += 1
                
                # --- STEP 1: VISION (Detection) ---
                detections = self.detector.track(frame)
                
                # --- STEP 2: PREDICTION (Forecasting) ---
                # Placeholder for streaming analytics
                
                # --- STEP 3: CONTROL (Decision) ---
                # Placeholder for signal decisions
                
                # --- STEP 4: VISUALIZATION ---
                if frame_id % 5 == 0: # Only draw every 5th frame for speed
                    self.detector.draw_detections(frame, detections)
                    cv2.imshow('Smart AI Traffic - Phase 5 Hub', frame)
                
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

if __name__ == "__main__":
    pipeline = SmartTrafficPipeline()
    pipeline.run()
                self._draw_status(frame, counts, forecast, action)
                
                if show:
                    cv2.imshow('Connected Traffic Intelligence (V+P+C)', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                if frame_id % 60 == 0:
                    logger.info(f"Frame {frame_id} | Live: {total_current} | Forecast: {forecast:.1f} | Signal: Lane {action}")

        finally:
            self.cap.release()
            cv2.destroyAllWindows()
            logger.info("Pipeline execution finished.")

    def _get_counts(self, detections):
        counts = {'car': 0, 'motorcycle': 0, 'bus': 0, 'truck': 0}
        for det in detections:
            label = det['label']
            if label in counts:
                counts[label] += 1
        return counts

    def _draw_status(self, frame, counts, forecast, action):
        """Draw unified pipeline status overlay."""
        h, w, _ = frame.shape
        # Top Dashboard
        cv2.rectangle(frame, (0, 0), (w, 60), (0, 0, 0), -1)
        
        # Live Stats
        status_text = f"LIVE: {sum(counts.values())} | FCST: {forecast:.1f} | SIGNAL: {action}"
        cv2.putText(frame, status_text, (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        
        # Signal Indicator (bottom right)
        cv2.circle(frame, (w - 50, 40), 20, (0, 255, 0), -1)
        cv2.putText(frame, f"L{action}", (w-65, 48), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 2)

if __name__ == "__main__":
    # Check for models or use default
    pipeline = SmartTrafficPipeline(
        video_source="data/traffic_sample.mp4",
        dqn_path="models/dqn_traffic.pth",
        lstm_path="models/traffic_lstm.pth"
    )
    pipeline.run()
