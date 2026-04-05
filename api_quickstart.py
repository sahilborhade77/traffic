#!/usr/bin/env python3
"""
Quick-start examples and utilities for the API and data aggregator.

Run this to test key components:
    python api_quickstart.py
"""

import sys
import os
import asyncio
import logging
from datetime import datetime, timedelta
import time

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from analytics.data_aggregator import TrafficDataAggregator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def demo_data_aggregator():
    """
    Demonstrate data aggregator functionality.
    """
    print("\n" + "="*80)
    print("TRAFFIC DATA AGGREGATOR DEMO")
    print("="*80 + "\n")

    # Initialize aggregator
    aggregator = TrafficDataAggregator(data_dir='data')

    # Simulate vehicle observations
    print("[CHART] Adding vehicle observations...")
    for i in range(100):
        lane = ['North', 'South', 'East', 'West'][i % 4]
        vehicle_class = ['car', 'truck', 'motorcycle'][i % 3]
        speed = 5 + (i % 15)
        aggregator.add_vehicle_observation(
            lane=lane,
            vehicle_class=vehicle_class,
            speed=float(speed),
            distance=float(speed * 30)
        )

    print(f"[OK] Added 100 vehicle observations")

    # Simulate wait times
    print("\n[TIME] Adding wait time observations...")
    for i in range(50):
        lane = ['North', 'South', 'East', 'West'][i % 4]
        vehicle_id = 1000 + i
        wait_time = 20 + (i % 60)
        aggregator.add_wait_time_observation(
            lane=lane,
            wait_time=float(wait_time),
            vehicle_type='car',
            vehicle_id=vehicle_id
        )

    print(f"[OK] Added 50 wait time observations")

    # Simulate violations
    print("\n[ALERT] Recording violations...")
    violation_types = ['red_light', 'speeding', 'illegal_turn']
    for i in range(15):
        lane = ['North', 'South', 'East', 'West'][i % 4]
        vehicle_id = 2000 + i
        violation_type = violation_types[i % 3]
        severity = ['low', 'medium', 'high', 'critical'][i % 4]
        aggregator.record_violation(
            lane=lane,
            violation_type=violation_type,
            vehicle_id=vehicle_id,
            severity=severity
        )

    print(f"[OK] Recorded 15 violations")

    # Get hourly statistics
    print("\n[STATS] HOURLY STATISTICS")
    print("-" * 80)
    hourly_stats = aggregator.get_hourly_statistics()
    for lane, stats in hourly_stats.items():
        print(f"\n{lane} Lane (Hour {stats.hour}:00):")
        print(f"  • Total Vehicles: {stats.total_vehicles}")
        print(f"  • Vehicle Breakdown: {stats.vehicle_breakdown}")
        print(f"  • Avg Wait Time: {stats.avg_wait_time:.1f}s")
        print(f"  • Max Wait Time: {stats.max_wait_time:.1f}s")
        print(f"  • Violations: {stats.total_violations}")
        print(f"  • Avg Speed: {stats.avg_vehicle_speed:.1f} m/s")
        print(f"  • Traffic Density: {stats.traffic_density:.1%}")
        print(f"  • Congestion: {stats.congestion_level}")

    # Get daily statistics
    print("\n[CALENDAR] DAILY STATISTICS")
    print("-" * 80)
    daily_stats = aggregator.get_daily_statistics()
    print(f"\nDate: {daily_stats.date} ({daily_stats.day_of_week})")
    print(f"  • Total Vehicles: {daily_stats.total_vehicles}")
    print(f"  • Vehicle Breakdown: {daily_stats.vehicle_breakdown}")
    print(f"  • Avg Wait Time: {daily_stats.avg_wait_time:.1f}s")
    print(f"  • Peak Hours: {daily_stats.peak_hours}")
    print(f"  • Busiest Hour: {daily_stats.busiest_hour}:00")
    print(f"  • Total Violations: {daily_stats.total_violations}")
    print(f"  • Avg Traffic Density: {daily_stats.avg_traffic_density:.1%}")
    print(f"  • Avg Vehicle Speed: {daily_stats.avg_vehicle_speed:.1f} m/s")

    # Per-lane breakdown
    print(f"\n  Per-Lane Breakdown:")
    for lane, lane_data in daily_stats.lanes.items():
        print(f"    {lane}:")
        print(f"      - Vehicles: {lane_data['vehicles']}")
        print(f"      - Violations: {lane_data['violations']}")
        print(f"      - Avg Wait Time: {lane_data['avg_wait_time']:.1f}s")

    # Peak hours analysis
    print("\n[FIRE] PEAK HOURS ANALYSIS")
    print("-" * 80)
    peak_hours = aggregator.get_peak_hours(limit=5)
    for hour, count in peak_hours:
        print(f"Hour {hour:02d}:00 - {count} vehicles")

    # Congestion index
    print("\n[CHART] CONGESTION INDEX")
    print("-" * 80)
    congestion = aggregator.get_congestion_index()
    level = (
        "[GREEN] LOW" if congestion < 0.3 else
        "[YELLOW] MEDIUM" if congestion < 0.6 else
        "[RED] HIGH" if congestion < 0.85 else
        "[RED] CRITICAL"
    )
    print(f"Current Congestion: {congestion:.2%} {level} LEVEL")

    # Summary report
    print("\n[REPORT] COMPREHENSIVE SUMMARY REPORT")
    print("-" * 80)
    report = aggregator.get_summary_report()
    print(f"\nTimestamp: {report['timestamp']}")
    print(f"Date: {report['date']}")
    print(f"Current Hour: {report['current_hour']:02d}:00")
    print(f"\nVehicles:")
    print(f"  • This Hour: {report['vehicles_this_hour']}")
    print(f"  • Today: {report['total_vehicles_today']}")
    print(f"\nViolations:")
    print(f"  • This Hour: {report['violations_this_hour']}")
    print(f"  • Today: {report['violations_today']}")
    print(f"\nTraffic Metrics:")
    print(f"  • Avg Wait Time: {report['avg_wait_time_seconds']:.1f}s")
    print(f"  • Peak Hours: {report['peak_hours']}")
    print(f"  • Busiest Hour: {report['busiest_hour']}:00")
    print(f"  • Congestion Index: {report['congestion_index']:.2%}")
    print(f"\nPer-Lane Status:")
    for lane, data in report['lanes'].items():
        print(f"  {lane}:")
        print(f"    - Vehicles: {data['vehicles']}")
        print(f"    - Violations: {data['violations']}")
        print(f"    - Avg Wait Time: {data['avg_wait_time']:.1f}s")
        print(f"    - Congestion: {data['congestion_level']}")

    # Export capabilities
    print("\n[SAVE] EXPORT CAPABILITIES")
    print("-" * 80)
    print("Data can be exported in the following formats:")
    print("  • hourly_stats.csv - Hourly statistics")
    print("  • daily_stats.csv - Daily statistics")
    print("  • JSON export functions available for custom analysis")
    print(f"\nData stored in: data/statistics/")

    print("\n" + "="*80)
    print("[OK] DEMO COMPLETE")
    print("="*80 + "\n")


def demo_api_endpoints():
    """
    Show example API calls (for when API is running).
    
    To test these in practice:
    1. Start API: uvicorn src.dashboard.api:app --reload
    2. Run:
       - curl http://localhost:8000/docs (interactive documentation)
       - curl http://localhost:8000/api/traffic/status
       - curl http://localhost:8000/api/analytics/hourly
       - etc.
    """
    print("\n" + "="*80)
    print("API EXAMPLE CALLS (when API is running)")
    print("="*80 + "\n")

    examples = {
        "Health Check": "curl http://localhost:8000/api/health",
        "Traffic Status (All Lanes)": "curl http://localhost:8000/api/traffic/status",
        "Traffic Status (North)": "curl http://localhost:8000/api/traffic/status?lane=North",
    }

    for description, command in examples.items():
        print(f"[API] {description}")
        print(f"      {command}\n")

    print("\nAPI DOCUMENTATION")
    print("-" * 80)
    print("When the API is running, visit:")
    print("  * http://localhost:8000/docs (Swagger UI)")
    print("  * http://localhost:8000/redoc (ReDoc)")
    print("\nThese provide interactive API testing and full documentation.\n")


def show_integration_example():
    """Show complete integration example code."""
    # Skip for now due to encoding
    return

    code = '''
# Complete integration example connecting all systems
import cv2
from src.vision.detector import YOLODetector
from src.vision.deepsort_tracker import DeepSORTTracker
from src.vision.red_light_integration import EnforcementSystem
from src.analytics.data_aggregator import TrafficDataAggregator

# Initialize
detector = YOLODetector(model_size='n')
tracker = DeepSORTTracker(fps=30.0)
enforcement = EnforcementSystem(enable_snapshots=True)
aggregator = TrafficDataAggregator()

# Configure
enforcement.configure_intersection(lanes)

# Process video
cap = cv2.VideoCapture('traffic.mp4')
frame_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Detection → Tracking → Enforcement
    detections = detector.detect(frame)
    active_tracks = tracker.update(detections, frame)
    signal_state = controller.get_state()
    
    enforcement_results = enforcement.process_frame(
        frame, active_tracks, signal_state, frame_count
    )

    # Aggregate data
    for track_id, track in active_tracks.items():
        aggregator.add_vehicle_observation(
            lane=determine_lane(track.position),
            vehicle_class=track.vehicle_class,
            speed=track.speed
        )

    # Record violations
    for violation in enforcement_results.get('violations', []):
        aggregator.record_violation(
            lane=violation.lane_name,
            violation_type='red_light',
            vehicle_id=violation.track_id
        )

    # Get summary statistics
    if frame_count % 100 == 0:
        report = aggregator.get_summary_report()
        print(f"Hour {report['current_hour']}: {report['vehicles_this_hour']} vehicles")

    frame_count += 1

cap.release()

# Export results
hourly_csv = aggregator.export_hourly_csv()
daily_csv = aggregator.export_daily_csv()
print(f"Exported: {hourly_csv}, {daily_csv}")
    '''

    print(code)
    print("\n" + "="*80 + "\n")


def main():
    """Run all demos."""
    print("\n" + "="*80)
    print("TRAFFIC ANALYTICS API & AGGREGATOR QUICKSTART")
    print("="*80)

    # Run data aggregator demo
    demo_data_aggregator()

    # Show API examples
    demo_api_endpoints()

    # Show integration example
    show_integration_example()

    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)

    print("\n1. Start the API:")
    print("   $ uvicorn src.dashboard.api:app --host 0.0.0.0 --port 8000 --reload")

    print("\n2. View API documentation:")
    print("   -> http://localhost:8000/docs")

    print("\n3. Test API endpoints (use browser or curl):")
    print("   -> http://localhost:8000/api/traffic/status")
    print("   -> http://localhost:8000/api/analytics/daily")

    print("\n4. Integrate into your system:")
    print("   from src.analytics.data_aggregator import TrafficDataAggregator")
    print("   aggregator = TrafficDataAggregator()")
    print("   # Add observations, get statistics, export reports")

    print("\n5. Monitor real-time updates via WebSocket:")
    print("   ws://localhost:8000/api/ws/traffic")
    print("   ws://localhost:8000/api/ws/camera")

    print("\nFor complete documentation, see:")
    print("   - API_DOCUMENTATION.md: Full API reference")
    print("   - src/analytics/data_aggregator.py: Aggregator code")
    print("   - src/dashboard/api.py: API implementation")
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
