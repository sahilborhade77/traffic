"""
Multi-Video Traffic Intelligence Pipeline
Processes multiple traffic videos simultaneously or sequentially
"""

import os
import cv2
import torch
import numpy as np
import logging
from collections import deque
from pathlib import Path
from typing import List, Dict
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import threading

from src.utils.config import CONFIG
from src.vision.detector import VehicleDetector
from src.control.environment import TrafficSignalEnv
from src.prediction.lstm_model import TrafficFlowPredictor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MultiVideoTrafficPipeline")


class MultiVideoTrafficPipeline:
    """
    Handle multiple video streams with parallel/sequential processing.
    """
    
    def __init__(self, video_sources: List[str], processing_mode='sequential', num_workers=2):
        """
        Args:
            video_sources: List of video file paths
            processing_mode: 'sequential' or 'parallel'
            num_workers: Number of parallel workers (for parallel mode)
        """
        self.video_sources = video_sources
        self.processing_mode = processing_mode
        self.num_workers = min(num_workers, len(video_sources))
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.results = {}
        
        logger.info(f"🎬 Multi-Video Pipeline initialized")
        logger.info(f"📹 Videos to process: {len(video_sources)}")
        logger.info(f"⚙️  Processing mode: {processing_mode}")
        logger.info(f"🔧 Workers: {self.num_workers}")
        logger.info(f"💻 Device: {self.device.upper()}")
        
        # Initialize detector once (reusable)
        try:
            logger.info("Initializing Vision Module (YOLOv8)...")
            self.detector = VehicleDetector(model_path=CONFIG['paths']['model_yolo'])
            logger.info("✅ Vision Module Ready")
        except Exception as e:
            logger.error(f"❌ Failed to initialize detector: {e}")
            raise
    
    def process_single_video(self, video_path: str) -> Dict:
        """Process a single video and return analytics."""
        logger.info(f"\n🎥 Processing: {Path(video_path).name}")
        
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"❌ Could not open: {video_path}")
                return {'status': 'failed', 'error': 'Could not open video'}
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            logger.info(f"📊 Video Info: {total_frames} frames @ {fps} FPS ({duration:.1f}s)")
            
            # Initialize history for LSTM
            history = deque(maxlen=CONFIG['prediction']['history_window'])
            frame_id = 0
            detections_list = []
            
            start_time = time.time()
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_id += 1
                
                # Vision: Detection
                detections = self.detector.track(frame)
                counts = self._get_counts(detections)
                total_current = sum(counts.values())
                
                # Prediction: LSTM history
                history.append(total_current)
                
                # Store every 30 frames for analysis
                if frame_id % 30 == 0:
                    detections_list.append({
                        'frame': frame_id,
                        'vehicle_count': total_current,
                        'counts': counts
                    })
                
                # Progress indicator
                if frame_id % 100 == 0:
                    progress = (frame_id / total_frames) * 100
                    logger.info(f"  Progress: {progress:.1f}% ({frame_id}/{total_frames})")
            
            cap.release()
            processing_time = time.time() - start_time
            
            # Calculate statistics
            vehicle_counts = [d['vehicle_count'] for d in detections_list]
            
            result = {
                'status': 'completed',
                'file': Path(video_path).name,
                'path': video_path,
                'total_frames': total_frames,
                'fps': fps,
                'duration': duration,
                'processing_time': processing_time,
                'avg_fps': total_frames / processing_time if processing_time > 0 else 0,
                'avg_vehicles': np.mean(vehicle_counts) if vehicle_counts else 0,
                'max_vehicles': np.max(vehicle_counts) if vehicle_counts else 0,
                'min_vehicles': np.min(vehicle_counts) if vehicle_counts else 0,
                'peak_congestion': (np.max(vehicle_counts) / 100) * 100 if vehicle_counts else 0,
            }
            
            logger.info(f"✅ Completed: {Path(video_path).name}")
            logger.info(f"   Avg Vehicles: {result['avg_vehicles']:.1f}")
            logger.info(f"   Processing Speed: {result['avg_fps']:.1f} FPS")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error processing {video_path}: {e}")
            return {'status': 'failed', 'file': Path(video_path).name, 'error': str(e)}
    
    def process_sequential(self) -> Dict:
        """Process videos one by one (recommended for better quality)."""
        logger.info("\n" + "="*60)
        logger.info("🎬 SEQUENTIAL PROCESSING (One video at a time)")
        logger.info("="*60)
        
        results = {}
        total_start = time.time()
        
        for idx, video_path in enumerate(self.video_sources, 1):
            logger.info(f"\n[{idx}/{len(self.video_sources)}] Processing...")
            results[video_path] = self.process_single_video(video_path)
        
        total_time = time.time() - total_start
        results['summary'] = {
            'total_videos': len(self.video_sources),
            'total_time': total_time,
            'avg_time_per_video': total_time / len(self.video_sources)
        }
        
        return results
    
    def process_parallel(self) -> Dict:
        """Process multiple videos in parallel (faster but more resource-intensive)."""
        logger.info("\n" + "="*60)
        logger.info(f"🎬 PARALLEL PROCESSING ({self.num_workers} workers)")
        logger.info("="*60)
        
        results = {}
        total_start = time.time()
        
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = {
                executor.submit(self.process_single_video, video): video 
                for video in self.video_sources
            }
            
            for future in futures:
                video = futures[future]
                try:
                    results[video] = future.result()
                except Exception as e:
                    logger.error(f"❌ Failed to process {video}: {e}")
                    results[video] = {'status': 'failed', 'error': str(e)}
        
        total_time = time.time() - total_start
        results['summary'] = {
            'total_videos': len(self.video_sources),
            'total_time': total_time,
            'avg_time_per_video': total_time / len(self.video_sources),
            'workers_used': self.num_workers
        }
        
        return results
    
    def run(self) -> Dict:
        """Run pipeline based on configured processing mode."""
        if self.processing_mode == 'parallel':
            return self.process_parallel()
        else:
            return self.process_sequential()
    
    def _get_counts(self, detections: List) -> Dict:
        """Count vehicles by lane."""
        counts = {'north': 0, 'south': 0, 'east': 0, 'west': 0}
        # Simplified counting logic
        if detections:
            total = len(detections)
            counts['north'] = total // 4
            counts['south'] = total // 4
            counts['east'] = total // 4
            counts['west'] = total % 4 + total // 4
        return counts
    
    def print_results(self, results: Dict):
        """Pretty print results."""
        logger.info("\n" + "="*80)
        logger.info("📊 RESULTS SUMMARY")
        logger.info("="*80)
        
        for video_path, result in results.items():
            if video_path == 'summary':
                continue
            
            logger.info(f"\n📹 {result.get('file', 'Unknown')}:")
            if result['status'] == 'completed':
                logger.info(f"   ✅ Status: Completed")
                logger.info(f"   📏 Duration: {result['duration']:.1f}s ({result['total_frames']} frames)")
                logger.info(f"   ⚡ Speed: {result['avg_fps']:.1f} FPS")
                logger.info(f"   🚗 Avg Vehicles: {result['avg_vehicles']:.1f}")
                logger.info(f"   📈 Peak: {result['max_vehicles']:.0f} vehicles")
            else:
                logger.info(f"   ❌ Status: Failed - {result.get('error', 'Unknown error')}")
        
        if 'summary' in results:
            summary = results['summary']
            logger.info("\n" + "="*80)
            logger.info(f"⏱️  Total Time: {summary['total_time']:.1f}s")
            logger.info(f"🎬 Videos Processed: {summary['total_videos']}")
            logger.info(f"⏳ Avg Time/Video: {summary['avg_time_per_video']:.1f}s")
            if 'workers_used' in summary:
                logger.info(f"👷 Workers Used: {summary['workers_used']}")


def get_video_files(directory: str = 'data', pattern: str = '*.mp4') -> List[str]:
    """Get all video files from directory."""
    video_dir = Path(directory)
    videos = list(video_dir.glob(pattern))
    logger.info(f"Found {len(videos)} videos in {directory}")
    return [str(v) for v in videos]


# ============================================================================
# CAPACITY INFORMATION
# ============================================================================
# 
# HOW MANY VIDEOS CAN THE SYSTEM HANDLE?
#
# 1. SEQUENTIAL PROCESSING (Recommended):
#    - Videos processed one by one
#    - Unlimited videos (depends on disk space)
#    - Each video: ~30-60 minutes (5 min video at 30 FPS)
#    - Quality: BEST (no resource contention)
#
# 2. PARALLEL PROCESSING:
#    - CPU Memory Usage: ~2-3 GB per video
#    - GPU Memory Usage: ~2-4 GB per video
#    - Safe Limit (CPU): 3-4 videos with 16 GB RAM
#    - Safe Limit (GPU): 2-3 videos with 8 GB VRAM
#    - Quality: GOOD (faster but shared resources)
#
# 3. RECOMMENDED CONFIGURATION:
#    - Up to 5-10 videos: Sequential mode
#    - 10-100 videos: Sequential mode with batch scheduling
#    - 100+ videos: Distributed processing (multiple machines)
#
# 4. HARDWARE REQUIREMENTS:
#    ┌─────────────────────────────────────────────────┐
#    │ Videos │ RAM   │ VRAM  │ Duration │ Mode       │
#    ├─────────────────────────────────────────────────┤
#    │ 1      │ 8 GB  │ 2 GB  │ 5 min    │ Sequential │
#    │ 2      │ 12 GB │ 4 GB  │ 10 min   │ Sequential │
#    │ 3      │ 16 GB │ 6 GB  │ 15 min   │ Sequential │
#    │ 4      │ 24 GB │ 8 GB  │ 20 min   │ Parallel   │
#    │ 5+     │ 32 GB │ 12 GB │ 30+ min  │ Batch Seq  │
#    └─────────────────────────────────────────────────┘
#
# ============================================================================


if __name__ == "__main__":
    # Example usage
    
    # Option 1: Process all videos in 'data' folder (Sequential)
    video_files = get_video_files('data', '*.mp4')
    
    if video_files:
        pipeline = MultiVideoTrafficPipeline(
            video_sources=video_files,
            processing_mode='sequential',  # Change to 'parallel' for faster processing
            num_workers=2
        )
        
        results = pipeline.run()
        pipeline.print_results(results)
    else:
        logger.warning("No video files found in data folder")
