import os
import argparse
from src.vision.detector import VehicleDetector
from src.vision.video_processor import TrafficVideoProcessor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Smart AI Traffic Module 1: Lane Tracking Demo")
    parser.add_argument("--input", default="data/traffic_sample.mp4", 
                        help="Path to the input video file")
    parser.add_argument("--output", default="data/tracking_result.mp4", 
                        help="Path to save the processed video")
    parser.add_argument("--csv", default="data/traffic_analytics.csv", 
                        help="Path to save the CSV analytics")
    parser.add_argument("--json", default="data/traffic_analytics.json", 
                        help="Path to save the JSON analytics")
    parser.add_argument("--show", action="store_true", default=True,
                        help="Whether to show the video in real-time")
    
    args = parser.parse_args()

    # Step 1: Ensure directories
    os.makedirs('data', exist_ok=True)
    os.makedirs('models', exist_ok=True)

    # Step 2: Define 4 Observation Zones for the Roundabout (N, S, E, W)
    # These cover the entry and exit points of the circle
    lane_setup = {
        'North Entry': [(0.40, 0.02), (0.60, 0.02), (0.60, 0.25), (0.40, 0.25)],
        'South Entry': [(0.40, 0.70), (0.60, 0.70), (0.60, 0.98), (0.40, 0.98)],
        'West Entry':  [(0.02, 0.40), (0.28, 0.40), (0.28, 0.60), (0.02, 0.60)],
        'East Entry':  [(0.70, 0.40), (0.98, 0.40), (0.98, 0.60), (0.70, 0.60)]
    }

    if not os.path.exists(args.input):
        logger.warning(f"File {args.input} not found.")
        return

    try:
        logger.info("Loading YOLOv8 Tracker (Small version for better distance detection)...")
        # Switched to yolov8s.pt for better accuracy with small vehicles from height
        detector = VehicleDetector(model_path='yolov8s.pt', tracker='bytetrack.yaml') 
        
        logger.info(f"Analyzing {args.input} with multi-lane tracking...")
        processor = TrafficVideoProcessor(args.input, detector, lane_definitions=lane_setup)
        
        processor.process(output_path=args.output, show=args.show)
        processor.save_results(csv_file=args.csv, json_file=args.json)
        
        logger.info(f"Module 1 Improved: Results available in {args.csv}")

    except Exception as e:
        logger.error(f"Demo failed: {e}")

if __name__ == "__main__":
    main()
