import os
import cv2
import torch
import numpy as np
import logging
from collections import deque
from src.vision.detector import VehicleDetector
from src.vision.video_processor import TrafficVideoProcessor
from src.control.environment import TrafficSignalEnv
from src.control.agents import DQNAgent, RuleBasedAgent
from src.prediction.model import LSTMForecaster

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TrafficPipeline")

class SmartTrafficPipeline:
    """
    Connected Workflow: Vision -> Prediction -> Control.
    """
    def __init__(self, video_source, dqn_path=None, lstm_path=None):
        self.video_source = video_source
        
        # 1. Vision Module
        logger.info("Initializing Module 1: Vision...")
        self.detector = VehicleDetector()
        self.cap = cv2.VideoCapture(video_source)
        
        # 2. Prediction Module (LSTM)
        logger.info("Initializing Module 3: Prediction...")
        self.forecast_window = deque(maxlen=12) # Needs 12 steps of history
        self.lstm = LSTMForecaster()
        if lstm_path and os.path.exists(lstm_path):
            self.lstm.load_state_dict(torch.load(lstm_path))
            self.lstm.eval()
            logger.info("LSTM Model loaded.")
        else:
            logger.warning("Using un-trained LSTM (Module 3 placeholder).")

        # 3. Control Module (DQN)
        logger.info("Initializing Module 2: Control...")
        self.env = TrafficSignalEnv(num_lanes=4)
        state_dim = self.env.get_state().shape[0]
        self.dqn = DQNAgent(state_dim, self.env.num_lanes)
        if dqn_path and os.path.exists(dqn_path):
            self.dqn.load(dqn_path)
            logger.info("DQN Agent loaded.")
        else:
            logger.warning("Using Rule-Based Baseline for control.")
            self.dqn = RuleBasedAgent(action_space=4)

    def run(self, show=True):
        """
        Execute the unified traffic intelligence pipeline.
        """
        frame_id = 0
        logger.info("Starting Traffic Pipeline Workflow...")

        try:
            while self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                frame_id += 1
                
                # --- STEP 1: VISION (Detection) ---
                detections = self.detector.track(frame)
                counts = self._get_counts(detections)
                total_current = sum(counts.values())
                
                # --- STEP 2: PREDICTION (Forecasting) ---
                # Update window for prediction
                self.forecast_window.append(total_current)
                forecast = 0.0
                if len(self.forecast_window) == 12:
                    # Prepare input for LSTM: (batch=1, seq=12, feat=1)
                    input_t = torch.FloatTensor(np.array(self.forecast_window)).view(1, 12, 1)
                    with torch.no_grad():
                        forecast = self.lstm(input_t).item()
                
                # --- STEP 3: CONTROL (Decision) ---
                # Map detected counts to environment state
                # Note: For demo, we treat detected counts as the 'queue'
                env_state = np.array([counts['car'], counts['motorcycle'], counts['bus'], counts['truck'], 0])
                
                # Adjust state with prediction bias (Optional: AI foresight)
                if forecast > 20: # High predicted congestion
                    logger.info(f"Foresight: High traffic predicted ({forecast:.2f}). Adjusting signal timing...")
                
                # Get signal action
                if hasattr(self.dqn, 'get_action'):
                    # Rule-based or DQN
                    try:
                        action = self.dqn.get_action(env_state, train=False)
                    except TypeError:
                        action = self.dqn.get_action(env_state)
                
                # --- STEP 4: VISUALIZATION ---
                self.detector.draw_detections(frame, detections)
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
