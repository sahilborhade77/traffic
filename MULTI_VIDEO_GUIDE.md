# Multi-Video Processing Guide

## How to Use Multiple Videos

### Method 1: Sequential Processing (Recommended)
Process videos one after another - **best quality**, **no resource conflicts**

```powershell
python multi_video_pipeline.py
```

**Best for:** 1-10 videos, long videos, resource-limited systems

---

### Method 2: Custom Script with Multiple Videos

Create a file called `process_videos.py`:

```python
from multi_video_pipeline import MultiVideoTrafficPipeline

# List of video files
videos = [
    'data/traffic_video_1.mp4',
    'data/traffic_video_2.mp4',
    'data/traffic_video_3.mp4',
]

# Sequential (one by one) - RECOMMENDED
pipeline = MultiVideoTrafficPipeline(
    video_sources=videos,
    processing_mode='sequential'
)

results = pipeline.run()
pipeline.print_results(results)
```

Run it:
```powershell
python process_videos.py
```

---

### Method 3: Parallel Processing (Faster but Resource-Heavy)

```python
from multi_video_pipeline import MultiVideoTrafficPipeline

videos = [
    'data/video1.mp4',
    'data/video2.mp4',
    'data/video3.mp4',
    'data/video4.mp4',
]

# Parallel with 2 workers
pipeline = MultiVideoTrafficPipeline(
    video_sources=videos,
    processing_mode='parallel',
    num_workers=2  # 2 videos at same time
)

results = pipeline.run()
pipeline.print_results(results)
```

---

## How Many Videos Can System Handle?

### 📊 Capacity Table

| Videos | RAM Needed | VRAM Needed | Processing Mode | Speed |
|--------|-----------|-----------|-----------------|-------|
| **1** | 8 GB | 2 GB | Sequential | Baseline |
| **2** | 12 GB | 4 GB | Sequential | 1x |
| **3-5** | 16 GB | 6 GB | Sequential | 1x |
| **5-10** | 24 GB | 8 GB | Sequential or Batch | 1x |
| **2-3** | 12-16 GB | 4-6 GB | Parallel (2 workers) | ~1.8x faster |
| **4-5** | 24 GB | 8 GB | Parallel (2 workers) | Limited by bottleneck |
| **10+** | 32 GB | 12 GB | Distributed/Batch | Custom |

---

### 🔧 Recommended Configuration by System

#### **Entry Level (Laptop)**
- **RAM:** 8-12 GB
- **GPU:** 2-4 GB VRAM
- **Process:** Sequential, 1 video at a time
- **Max Concurrent:** 1

```python
pipeline = MultiVideoTrafficPipeline(
    video_sources=videos,
    processing_mode='sequential'
)
```

---

#### **Mid-Range (Workstation)**
- **RAM:** 16 GB
- **GPU:** 6-8 GB VRAM
- **Process:** Sequential or 2 parallel
- **Max Concurrent:** 2

```python
# Option A: Safe Sequential
pipeline = MultiVideoTrafficPipeline(
    video_sources=videos,
    processing_mode='sequential'
)

# Option B: Faster Parallel (2 at a time)
pipeline = MultiVideoTrafficPipeline(
    video_sources=videos,
    processing_mode='parallel',
    num_workers=2
)
```

---

#### **High-End (Server)**
- **RAM:** 32+ GB
- **GPU:** 12+ GB VRAM
- **Process:** Parallel with batching
- **Max Concurrent:** 3-4

```python
pipeline = MultiVideoTrafficPipeline(
    video_sources=videos,
    processing_mode='parallel',
    num_workers=3
)
```

---

## Quick Example Commands

### Process all videos in `data/` folder:
```powershell
python -c "
from multi_video_pipeline import MultiVideoTrafficPipeline, get_video_files
videos = get_video_files('data')
pipeline = MultiVideoTrafficPipeline(videos, 'sequential')
pipeline.run()
"
```

### Process specific videos:
```powershell
python -c "
from multi_video_pipeline import MultiVideoTrafficPipeline
videos = ['data/video1.mp4', 'data/video2.mp4']
pipeline = MultiVideoTrafficPipeline(videos, 'sequential')
results = pipeline.run()
pipeline.print_results(results)
"
```

### Process with performance monitoring:
```python
import time
from multi_video_pipeline import MultiVideoTrafficPipeline

videos = ['data/video1.mp4', 'data/video2.mp4', 'data/video3.mp4']
pipeline = MultiVideoTrafficPipeline(videos, 'sequential')

start = time.time()
results = pipeline.run()
total_time = time.time() - start

print(f"Total time: {total_time:.1f}s")
print(f"Avg per video: {total_time/len(videos):.1f}s")
print(f"Total efficiency: {results['summary']['avg_time_per_video']:.1f}s/video")
```

---

## Performance Tips

### ✅ For Best Results:
1. Use **Sequential mode** for 1-5 videos
2. Use **Parallel mode** only with 16+ GB RAM and 8+ GB VRAM
3. **Close other apps** before processing
4. **Use SSD** for better I/O performance
5. **Set GPU priority** for Streamlit dashboard

### ⚡ Speed Optimization:
- Sequential: ~50-100 FPS (depends on video)
- Parallel (2 workers): ~40-70 FPS per worker
- Batch processing: Process multiple times of day

### 💾 Storage Requirements:
- Each video: ~2-5 MB per minute
- 10 videos (5 min each): ~100-250 MB disk
- Results only: ~1 MB per video (CSV/JSON)

---

## Environment Variables (Optional)

```powershell
# Save this to .env.multi_video

# Processing configuration
PROCESSING_MODE=sequential
NUM_WORKERS=2

# Resource limits
MAX_RAM_PERCENT=80
MAX_GPU_PERCENT=80

# Video settings
MIN_VIDEO_FPS=20
MAX_VIDEO_DURATION=3600  # seconds
```

Load in script:
```python
from dotenv import load_dotenv
import os
load_dotenv('.env.multi_video')

num_workers = int(os.getenv('NUM_WORKERS', 2))
```

---

## Summary

| Mode | Speed | Quality | Resources | Best For |
|------|-------|---------|-----------|----------|
| **Sequential** | 1x | ⭐⭐⭐⭐⭐ | Low | All videos |
| **Parallel (2)** | ~1.8x | ⭐⭐⭐⭐ | Medium | 2-4 videos |
| **Parallel (4+)** | Variable | ⭐⭐⭐ | High | High-end servers |

**Recommendation:** Start with **Sequential mode** for 1-5 videos. Scale up as needed! 🚀
