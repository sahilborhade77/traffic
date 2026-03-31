import os
import argparse
from src.vision.detector import VehicleDetector
from src.vision.video_processor import TrafficVideoProcessor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Smart AI Traffic Module 1: Vehicle Detection Demo")
    parser.add_argument("--input", default="data/traffic_sample.mp4", 
                        help="Path to the input video file")
    parser.add_argument("--output", default="data/output_result.mp4", 
                        help="Path to save the processed video")
    parser.add_argument("--stats", default="data/stats.csv", 
                        help="Path to save the counting stats CSV")
    parser.add_argument("--show", action="store_true", default=True,
                        help="Whether to show the video in real-time (default: True)")
    
    args = parser.parse_args()

    # Step 1: Ensure directories exist
    os.makedirs('data', exist_ok=True)
    os.makedirs('models', exist_ok=True)

    # Step 2: Check for input video
    if not os.path.exists(args.input):
        logger.warning(f"Input file {args.input} not found!")
        logger.info("Please place a traffic video file at 'data/traffic_sample.mp4' or provide a path via --input.")
        # Alternatively, you can download a sample video here if desired.
        return

    # Step 3: Initialize Detection & Processing
    try:
        logger.info("Initializing Vehicle Detector...")
        detector = VehicleDetector() # Loads yolov8n.pt by default (downloads if not present)
        
        logger.info(f"Starting Video Processing for {args.input}...")
        processor = TrafficVideoProcessor(args.input, detector)
        
        # Step 4: Run loop
        processor.process(output_path=args.output, show=args.show)
        
        # Step 5: Save CSV results
        processor.save_stats_csv(args.stats)
        
        logger.info(f"Demo complete! Results saved to {args.output} and {args.stats}.")

    except Exception as e:
        logger.error(f"Failed to run demo: {e}")

if __name__ == "__main__":
    main()
