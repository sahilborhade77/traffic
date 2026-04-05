#!/usr/bin/env python3
"""
YOLO Model Benchmarking Script

This script benchmarks different YOLO versions (v5, v8, v11) for vehicle detection
across multiple metrics: FPS, latency, memory usage, and detection accuracy.

Metrics measured:
- FPS (Frames Per Second): Inference speed
- Latency: Average inference time per frame
- Memory Usage: Peak GPU/CPU memory consumption
- Accuracy: Vehicle detection count (proxy metric - requires ground truth for true accuracy)

Usage:
    python benchmark_yolo.py [--models yolov5s yolov8s yolov11s] [--input image.jpg] [--iterations 100]
"""

import argparse
import time
import torch
import cv2
import numpy as np
import psutil
import os
import logging
from ultralytics import YOLO
from typing import Dict, List, Tuple
import gc

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YOLOBenchmarker:
    """
    Benchmarks YOLO models for vehicle detection performance.
    """

    def __init__(self, models: List[str], input_path: str, iterations: int = 100):
        """
        Initialize the benchmarker.

        Args:
            models: List of YOLO model names (e.g., ['yolov5s', 'yolov8s', 'yolov11s'])
            input_path: Path to test image or video
            iterations: Number of inference iterations for benchmarking
        """
        self.models = models
        self.input_path = input_path
        self.iterations = iterations
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.vehicle_classes = [2, 3, 5, 7]  # COCO classes: car, motorcycle, bus, truck

        logger.info(f"Using device: {self.device}")
        logger.info(f"Models to benchmark: {self.models}")
        logger.info(f"Test input: {input_path}")
        logger.info(f"Iterations: {iterations}")

    def load_test_data(self) -> Tuple[np.ndarray, bool]:
        """
        Load test image or extract frame from video.

        Returns:
            Tuple of (image, is_video)
        """
        if not os.path.exists(self.input_path):
            raise FileNotFoundError(f"Test file not found: {self.input_path}")

        if self.input_path.lower().endswith(('.mp4', '.avi', '.mov')):
            # Extract first frame from video
            cap = cv2.VideoCapture(self.input_path)
            ret, frame = cap.read()
            cap.release()
            if not ret:
                raise ValueError("Could not read frame from video")
            return frame, True
        else:
            # Load image
            image = cv2.imread(self.input_path)
            if image is None:
                raise ValueError("Could not load image")
            return image, False

    def benchmark_model(self, model_name: str) -> Dict:
        """
        Benchmark a single YOLO model.

        Args:
            model_name: Name of the model to benchmark

        Returns:
            Dictionary with benchmark results
        """
        logger.info(f"Benchmarking {model_name}...")

        try:
            # Load model
            model = YOLO(f"{model_name}.pt")
            model.to(self.device)

            # Load test data
            test_image, is_video = self.load_test_data()

            # Warmup
            logger.info("Performing warmup...")
            for _ in range(5):
                _ = model(test_image, verbose=False)

            # Clear cache
            if self.device == 'cuda':
                torch.cuda.empty_cache()
            gc.collect()

            # Measure memory before
            memory_before = self._get_memory_usage()

            # Benchmark inference
            latencies = []
            detections_count = 0

            start_time = time.perf_counter()

            for i in range(self.iterations):
                iter_start = time.perf_counter()

                results = model(test_image, verbose=False, conf=0.25, iou=0.45)

                iter_end = time.perf_counter()
                latencies.append(iter_end - iter_start)

                # Count vehicle detections
                if i == 0:  # Only count for first iteration to avoid duplicates
                    for result in results:
                        if result.boxes is not None:
                            detections_count += len(result.boxes)

            end_time = time.perf_counter()

            # Measure memory after
            memory_after = self._get_memory_usage()

            # Calculate metrics
            total_time = end_time - start_time
            avg_latency = np.mean(latencies)
            fps = self.iterations / total_time
            peak_memory = max(memory_after - memory_before)

            results = {
                'model': model_name,
                'fps': round(fps, 2),
                'avg_latency_ms': round(avg_latency * 1000, 2),
                'peak_memory_mb': round(peak_memory, 2),
                'detections_count': detections_count,
                'total_time': round(total_time, 2),
                'iterations': self.iterations
            }

            logger.info(f"{model_name} Results: FPS={results['fps']}, Latency={results['avg_latency_ms']}ms, "
                       f"Memory={results['peak_memory_mb']}MB, Detections={detections_count}")

            return results

        except Exception as e:
            logger.error(f"Error benchmarking {model_name}: {e}")
            return {
                'model': model_name,
                'error': str(e),
                'fps': 0,
                'avg_latency_ms': 0,
                'peak_memory_mb': 0,
                'detections_count': 0
            }

    def _get_memory_usage(self) -> float:
        """
        Get current memory usage in MB.

        Returns:
            Memory usage in MB
        """
        if self.device == 'cuda':
            # GPU memory
            return torch.cuda.memory_allocated() / 1024 / 1024
        else:
            # CPU memory
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024

    def run_benchmarks(self) -> List[Dict]:
        """
        Run benchmarks for all models.

        Returns:
            List of benchmark results
        """
        results = []

        for model_name in self.models:
            result = self.benchmark_model(model_name)
            results.append(result)

        return results

    def print_results(self, results: List[Dict]):
        """
        Print benchmark results in a formatted table.
        """
        print("\n" + "="*80)
        print("YOLO Vehicle Detection Benchmark Results")
        print("="*80)
        print("<10")
        print("-"*80)

        for result in results:
            if 'error' in result:
                print("<10")
            else:
                print("<10")

        print("="*80)
        print("Note: Detection count is a proxy metric. True accuracy requires ground truth data.")
        print("For accurate mAP/precision/recall, use a validation dataset with annotations.")

def main():
    parser = argparse.ArgumentParser(description="Benchmark YOLO models for vehicle detection")
    parser.add_argument(
        '--models',
        nargs='+',
        default=['yolov5s', 'yolov8s', 'yolov11s'],
        help='YOLO models to benchmark (default: yolov5s yolov8s yolov11s)'
    )
    parser.add_argument(
        '--input',
        default='data/traffic_sample.mp4',
        help='Path to test image or video file'
    )
    parser.add_argument(
        '--iterations',
        type=int,
        default=100,
        help='Number of inference iterations (default: 100)'
    )
    parser.add_argument(
        '--output',
        help='Output CSV file for results'
    )

    args = parser.parse_args()

    try:
        # Initialize benchmarker
        benchmarker = YOLOBenchmarker(args.models, args.input, args.iterations)

        # Run benchmarks
        results = benchmarker.run_benchmarks()

        # Print results
        benchmarker.print_results(results)

        # Save to CSV if requested
        if args.output:
            import pandas as pd
            df = pd.DataFrame(results)
            df.to_csv(args.output, index=False)
            logger.info(f"Results saved to {args.output}")

    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())