"""
Phase 9: Scalability Features - Integration Demo

Demonstrates integration of Load Balancer, Redis Cache, and Structured Logging
for a production-ready distributed traffic management system.

Features shown:
- Load balancer with health checks
- Cache management with invalidation
- Structured logging with performance tracking
- Complete API request lifecycle
- Error handling and recovery
"""

import time
import json
from datetime import datetime
from typing import Dict, List

# Import Phase 9 modules
from src.utils.load_balancer import RoundRobinLoadBalancer
from src.utils.cache_manager import CacheManager, RedisCache
from src.utils.structured_logger import StructuredLogger, log_function_call, log_performance


class Phase9Demonstrator:
    """Demonstrates Phase 9 scalability features."""
    
    def __init__(self):
        """Initialize demo with all Phase 9 components."""
        # Initialize load balancer
        self.load_balancer = RoundRobinLoadBalancer(
            max_consecutive_failures=3,
            timeout=5.0
        )
        
        # Initialize cache
        self.cache = CacheManager(
            redis_cache=RedisCache(
                host='localhost',
                port=6379,
                ttl=300,
                fallback_enabled=True
            )
        )
        
        # Initialize structured logger
        self.logger = StructuredLogger(
            name='phase9_demo',
            log_level='INFO',
            json_format=True
        )
        
        self.logger.info("Phase 9 Demonstrator initialized")
    
    def demo_load_balancer(self) -> None:
        """Demonstrate load balancer functionality."""
        print("\n" + "="*80)
        print("PHASE 9 STEP 28: LOAD BALANCER DEMONSTRATION")
        print("="*80)
        
        self.logger.info("Starting load balancer demo")
        
        # Add GPU instances
        print("\n[1] Adding GPU instances...")
        instances = [
            ("gpu-north-1", "192.168.1.100", 8001, 0),
            ("gpu-north-2", "192.168.1.101", 8001, 0),
            ("gpu-south-1", "192.168.1.102", 8001, 1),
            ("gpu-south-2", "192.168.1.103", 8001, 1),
        ]
        
        for instance_id, host, port, gpu_idx in instances:
            self.load_balancer.add_instance(instance_id, host, port, gpu_idx)
            print(f"  ✓ Added: {instance_id} at {host}:{port}")
        
        # Simulate round-robin selection
        print("\n[2] Round-robin instance selection...")
        cameras = ['north-1', 'north-2', 'south-1', 'south-2', 'north-1', 'north-2']
        
        for camera in cameras:
            instance = self.load_balancer.get_instance_for_stream(camera)
            if instance:
                print(f"  Camera {camera:10} -> {instance.instance_id} ({instance.url})")
                
                # Simulate request
                duration_ms = 45.2 if 'north' in camera else 38.5
                self.load_balancer.record_request_success(instance.instance_id, duration_ms)
        
        # Display statistics
        print("\n[3] Load balancer statistics...")
        stats = self.load_balancer.get_statistics()
        
        print(f"\n  Total instances: {stats['total_instances']}")
        print(f"  Healthy instances: {stats['healthy_instances']}")
        print(f"  Active streams: {stats['active_stream_assignments']}")
        
        print("\n  Instance Details:")
        for inst_id, inst_data in stats['instances'].items():
            print(f"    {inst_id}:")
            print(f"      - Status: {inst_data['status']}")
            print(f"      - Success rate: {inst_data['success_rate']}")
            print(f"      - Avg response: {inst_data['avg_response_time_ms']} ms")
            print(f"      - Total requests: {inst_data['total_requests']}")
        
        # Show health summary
        print("\n[4] Health check summary...")
        health = self.load_balancer.get_health_summary()
        print(f"  Total instances: {health['total_instances']}")
        print(f"  Healthy: {health['healthy_instances']}")
        print(f"  Unhealthy: {health['unhealthy_instances']}")
        print(f"  Health %: {health['health_percentage']:.1f}%")
        print(f"  Avg response time: {health['avg_response_time_ms']:.2f} ms")
        
        self.logger.info("Load balancer demo completed", stats)
    
    def demo_cache_manager(self) -> None:
        """Demonstrate caching functionality."""
        print("\n" + "="*80)
        print("PHASE 9 STEP 29: REDIS CACHING DEMONSTRATION")
        print("="*80)
        
        self.logger.info("Starting cache manager demo")
        
        # Cache traffic data
        print("\n[1] Caching traffic analytics...")
        
        lane_statuses = {
            'North': {'vehicle_count': 45, 'avg_speed': 32, 'wait_time': 42},
            'South': {'vehicle_count': 38, 'avg_speed': 35, 'wait_time': 28},
            'East': {'vehicle_count': 52, 'avg_speed': 28, 'wait_time': 58},
            'West': {'vehicle_count': 41, 'avg_speed': 31, 'wait_time': 48},
        }
        
        for lane, status in lane_statuses.items():
            self.cache.cache_lane_status(lane, status, ttl=60)
            print(f"  ✓ Cached: {lane} traffic status")
        
        # Retrieve cached data
        print("\n[2] Retrieving cached data...")
        
        for lane in lane_statuses.keys():
            cached = self.cache.get_lane_status(lane)
            if cached:
                print(f"  ✓ Retrieved: {lane}")
                print(f"    - Vehicle count: {cached['vehicle_count']}")
                print(f"    - Avg speed: {cached['avg_speed']} km/h")
                print(f"    - Wait time: {cached['wait_time']} sec")
        
        # Cache hourly and daily stats
        print("\n[3] Caching hourly and daily statistics...")
        
        hourly_data = {
            'total_vehicles': 850,
            'avg_speed': 31.5,
            'violations': 12,
            'peak_time': '18:00'
        }
        
        self.cache.cache_hourly_stats('2026-04-02', 18, hourly_data, ttl=3600)
        print(f"  ✓ Cached hourly stats for 18:00")
        
        daily_data = {
            'total_vehicles': 18450,
            'avg_speed': 30.2,
            'violations': 287,
            'peak_hour': 18
        }
        
        self.cache.cache_daily_stats('2026-04-02', daily_data, ttl=86400)
        print(f"  ✓ Cached daily stats")
        
        # Demonstrate cache invalidation
        print("\n[4] Demonstrating cache invalidation...")
        print("  Invalidating all 'North' lane caches on new detection...")
        
        invalidated = self.cache.invalidate_on_detection('North')
        print(f"  ✓ Invalidated cache entries for North lane")
        
        # Verify invalidation
        cached = self.cache.get_lane_status('North')
        if cached is None:
            print(f"  ✓ Confirmed: North lane cache invalidated")
        else:
            print(f"  ✗ Cache still exists")
        
        # Re-cache after invalidation
        self.cache.cache_lane_status('North', lane_statuses['North'], ttl=60)
        cached = self.cache.get_lane_status('North')
        if cached:
            print(f"  ✓ North lane cache restored")
        
        # Show cache statistics
        print("\n[5] Cache statistics...")
        stats = self.cache.get_cache_status()
        
        print(f"  Cache type: {stats['cache_type']}")
        print(f"  Status: {stats['using_fallback'] and 'Fallback' or 'Redis'}")
        
        cache_stats = stats['stats']
        print(f"  Hit rate: {cache_stats['hit_rate']}")
        print(f"  Total accesses: {cache_stats['total_accesses']}")
        print(f"  Cache items (memory): {stats['memory_cache_size']}")
        
        self.logger.info("Cache manager demo completed", stats)
    
    def demo_structured_logging(self) -> None:
        """Demonstrate structured logging."""
        print("\n" + "="*80)
        print("PHASE 9 STEP 30: STRUCTURED LOGGING DEMONSTRATION")
        print("="*80)
        
        # Create logger for demo
        demo_logger = StructuredLogger('traffic_api', log_level='DEBUG')
        
        print("\n[1] Basic logging with context...")
        
        demo_logger.info("Application started", {
            'version': '1.0.0',
            'environment': 'production',
            'timestamp': datetime.now().isoformat()
        })
        print("  ✓ Logged: Application started")
        
        # Log vehicle detections
        print("\n[2] Logging vehicle detections...")
        
        detections = [
            ('car', 0.98, (450, 320), 45.2, 'North'),
            ('truck', 0.95, (520, 280), 32.1, 'North'),
            ('motorcycle', 0.92, (380, 340), 58.5, 'North'),
        ]
        
        for class_name, confidence, position, speed, lane in detections:
            demo_logger.log_detection(
                track_id=int(datetime.now().timestamp() * 1000) % 10000,
                class_name=class_name,
                confidence=confidence,
                position=position,
                speed=speed,
                lane=lane
            )
            print(f"  ✓ Logged detection: {class_name} (confidence: {confidence:.2%})")
        
        # Log API requests
        print("\n[3] Logging API requests...")
        
        requests = [
            ('GET', '/api/traffic/status', 200, 42.5, {'lane': 'North'}),
            ('GET', '/api/analytics/hourly', 200, 125.3, None),
            ('POST', '/api/signal/control', 201, 38.2, {'signal_id': 'north-1'}),
            ('GET', '/api/violations', 200, 89.5, {'limit': 100}),
        ]
        
        for method, path, status, duration, ctx in requests:
            demo_logger.log_request(method, path, status, duration, ctx)
            print(f"  ✓ Logged: {method} {path} -> {status} ({duration:.1f}ms)")
        
        # Log performance metrics
        print("\n[4] Logging performance metrics...")
        
        demo_logger.info("Performance snapshot", {
            'frame_processing_ms': 32.5,
            'detection_inference_ms': 28.3,
            'tracking_ms': 4.2,
            'fps': 30.8
        })
        print("  ✓ Logged: Performance metrics")
        
        # Demonstrate timer context manager
        print("\n[5] Using timer context manager...")
        
        with demo_logger.timer('camera_frame_processing', {'camera': 'north-1'}):
            # Simulate processing
            time.sleep(0.05)
        print("  ✓ Timed: Camera frame processing (50ms)")
        
        # Log errors with context
        print("\n[6] Error logging...")
        
        try:
            # Simulate an error
            raise ValueError("Invalid camera configuration")
        except Exception as e:
            demo_logger.error("Camera initialization failed", {
                'camera_id': 'north-1',
                'error': str(e),
                'retry_count': 3
            })
            print(f"  ✓ Logged: Exception with context")
        
        # Show log directory
        print("\n[7] Log files created...")
        log_dir = demo_logger.log_dir
        for log_file in log_dir.glob(f"{demo_logger.name}*"):
            size_kb = log_file.stat().st_size / 1024
            print(f"  ✓ {log_file.name} ({size_kb:.1f} KB)")
    
    def demo_integrated_system(self) -> None:
        """Demonstrate all components working together."""
        print("\n" + "="*80)
        print("PHASE 9: INTEGRATED SCALABILITY SYSTEM")
        print("="*80)
        
        self.logger.info("Starting integrated system demo")
        
        print("\n[1] Processing camera streams with load balancing and caching...")
        
        # Simulate processing 5 camera streams
        streams = [
            {'id': 'north-1', 'vehicle_count': 45},
            {'id': 'north-2', 'vehicle_count': 38},
            {'id': 'south-1', 'vehicle_count': 52},
            {'id': 'east-1', 'vehicle_count': 48},
            {'id': 'west-1', 'vehicle_count': 41},
        ]
        
        for stream in streams:
            # Get instance from load balancer
            instance = self.load_balancer.get_instance_for_stream(stream['id'])
            
            if instance:
                # Check cache first
                cached = self.cache.get_lane_status(stream['id'].split('-')[0])
                
                if cached:
                    print(f"  [{stream['id']}] Cache HIT - served from cache")
                    self.logger.debug(f"Cache hit for {stream['id']}")
                else:
                    # Process on GPU instance
                    duration_ms = 45.2
                    self.load_balancer.record_request_success(instance.instance_id, duration_ms)
                    
                    # Cache result
                    result = {
                        'stream_id': stream['id'],
                        'vehicle_count': stream['vehicle_count'],
                        'processed_at': datetime.now().isoformat(),
                        'processing_time_ms': duration_ms
                    }
                    
                    self.cache.cache_lane_status(
                        stream['id'].split('-')[0],
                        result,
                        ttl=60
                    )
                    
                    print(f"  [{stream['id']}] Processed on {instance.instance_id} ({duration_ms:.1f}ms) -> Cached")
                    self.logger.info(f"Stream processed and cached: {stream['id']}", result)
        
        # Show final statistics
        print("\n[2] System statistics...")
        
        lb_stats = self.load_balancer.get_health_summary()
        cache_stats = self.cache.get_cache_status()
        
        print(f"\n  Load Balancer:")
        print(f"    - Total instances: {lb_stats['total_instances']}")
        print(f"    - Health: {lb_stats['health_percentage']:.1f}%")
        print(f"    - Avg response: {lb_stats['avg_response_time_ms']:.2f} ms")
        
        print(f"\n  Cache:")
        print(f"    - Type: {cache_stats['cache_type']}")
        print(f"    - Hit rate: {cache_stats['stats']['hit_rate']}")
        print(f"    - Items: {cache_stats['memory_cache_size']}")
        
        print("\n[3] Production-ready features...")
        print("  ✓ Automatic load balancing across GPU instances")
        print("  ✓ Health checks with automatic failover")
        print("  ✓ Redis caching with automatic invalidation")
        print("  ✓ Fallback to in-memory cache if Redis unavailable")
        print("  ✓ Structured JSON logging")
        print("  ✓ Performance metrics tracking")
        print("  ✓ Error handling with context")
        print("  ✓ Log rotation and retention")
        
        self.logger.info("Integrated system demo completed successfully")


def run_demo():
    """Run complete Phase 9 demonstration."""
    print("\n")
    print("#" * 80)
    print("# PHASE 9: SCALABILITY FEATURES DEMONSTRATION")
    print("# Steps 28-30: Load Balancer, Redis Caching, Structured Logging")
    print("#" * 80)
    
    demo = Phase9Demonstrator()
    
    # Run individual demonstrations
    demo.demo_load_balancer()
    demo.demo_cache_manager()
    demo.demo_structured_logging()
    demo.demo_integrated_system()
    
    print("\n" + "="*80)
    print("PHASE 9 DEMONSTRATION COMPLETED")
    print("="*80)
    print("\nLog files have been created in: logs/")
    print("Check logs/phase9_demo.log for detailed debug information")
    print()


if __name__ == "__main__":
    run_demo()
