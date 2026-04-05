#!/usr/bin/env python
"""
Quick example: Process multiple videos
Run: python example_multi_video.py
"""

from multi_video_pipeline import MultiVideoTrafficPipeline, get_video_files
import sys

def main():
    print("=" * 70)
    print("🎬 TRAFFIC INTELLIGENCE - MULTI-VIDEO PROCESSOR")
    print("=" * 70)
    
    # Option 1: Auto-detect all MP4 files in 'data' folder
    print("\n1️⃣ Scanning for videos in 'data' folder...")
    videos = get_video_files('data', '*.mp4')
    
    if not videos:
        print("❌ No videos found! Please add MP4 files to the 'data' folder")
        print("   Example: data/traffic_video_1.mp4")
        print("   Example: data/traffic_video_2.mp4")
        return
    
    # Option 2: Manually specify videos (uncomment to use)
    # videos = [
    #     'data/traffic_sample.mp4',
    #     'data/traffic_video_2.mp4',
    #     'data/traffic_video_3.mp4',
    # ]
    
    print(f"✅ Found {len(videos)} video(s):")
    for i, v in enumerate(videos, 1):
        print(f"   {i}. {v}")
    
    # Choose processing mode
    print("\n2️⃣ Choose processing mode:")
    print("   [1] Sequential (One video at a time) - RECOMMENDED")
    print("   [2] Parallel (Multiple videos at once) - Faster but resource-heavy")
    
    mode_choice = input("   Select (1 or 2) [default: 1]: ").strip() or "1"
    processing_mode = "parallel" if mode_choice == "2" else "sequential"
    num_workers = 2
    
    if processing_mode == "parallel":
        worker_input = input("   Number of parallel workers (1-4) [default: 2]: ").strip() or "2"
        try:
            num_workers = min(int(worker_input), len(videos), 4)
        except:
            num_workers = 2
    
    print("\n3️⃣ Starting pipeline...")
    print(f"   Mode: {processing_mode.upper()}")
    if processing_mode == "parallel":
        print(f"   Workers: {num_workers}")
    
    # Initialize and run pipeline
    try:
        pipeline = MultiVideoTrafficPipeline(
            video_sources=videos,
            processing_mode=processing_mode,
            num_workers=num_workers
        )
        
        results = pipeline.run()
        pipeline.print_results(results)
        
        print("\n" + "=" * 70)
        print("✅ PROCESSING COMPLETE")
        print("=" * 70)
        
        # Summary statistics
        if 'summary' in results:
            summary = results['summary']
            completed = sum(1 for r in results.values() 
                          if isinstance(r, dict) and r.get('status') == 'completed')
            print(f"\n📊 Summary:")
            print(f"   Total Videos: {summary['total_videos']}")
            print(f"   Completed: {completed}")
            print(f"   Total Time: {summary['total_time']:.1f} seconds")
            print(f"   Avg per Video: {summary['avg_time_per_video']:.1f} seconds")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
