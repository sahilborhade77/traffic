"""
Load Balancer for Distributed GPU Processing

Implements round-robin load balancing with health checks for distributing
camera streams across multiple GPU instances. Supports automatic failover
and recovery of unhealthy instances.

Features:
- Round-robin instance selection
- Periodic health checks (HTTP GET)
- Automatic removal of unhealthy instances
- Automatic recovery of recovered instances
- Stream routing by ID or weight
- Real-time instance statistics

Author: Traffic Intelligence Team
Version: 1.0.0
"""

import time
import threading
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import deque
from enum import Enum
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class InstanceStatus(Enum):
    """Health status of a GPU instance."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class GpuInstance:
    """Represents a GPU instance for processing."""
    instance_id: str
    host: str
    port: int
    gpu_index: int = 0
    
    # Status tracking
    status: InstanceStatus = InstanceStatus.UNKNOWN
    last_health_check: Optional[datetime] = None
    consecutive_failures: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    
    # Performance tracking
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    @property
    def url(self) -> str:
        """Get instance URL."""
        return f"http://{self.host}:{self.port}"
    
    @property
    def health_endpoint(self) -> str:
        """Get health check endpoint."""
        return f"{self.url}/api/health"
    
    @property
    def avg_response_time(self) -> float:
        """Get average response time in milliseconds."""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)
    
    @property
    def success_rate(self) -> float:
        """Get request success rate."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    def record_response_time(self, duration_ms: float) -> None:
        """Record response time for performance tracking."""
        self.response_times.append(duration_ms)
    
    def record_success(self) -> None:
        """Record successful request."""
        self.total_requests += 1
        self.successful_requests += 1
        self.consecutive_failures = 0
    
    def record_failure(self) -> None:
        """Record failed request."""
        self.total_requests += 1
        self.consecutive_failures += 1
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for reporting."""
        return {
            'instance_id': self.instance_id,
            'url': self.url,
            'status': self.status.value,
            'gpu_index': self.gpu_index,
            'consecutive_failures': self.consecutive_failures,
            'total_requests': self.total_requests,
            'success_rate': f"{self.success_rate:.2f}%",
            'avg_response_time_ms': f"{self.avg_response_time:.2f}",
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None
        }


class RoundRobinLoadBalancer:
    """
    Round-robin load balancer for distributing requests across GPU instances.
    
    Features:
    - Automatic round-robin selection
    - Health checking with configurable intervals
    - Automatic failover to healthy instances
    - Per-camera stream assignment
    - Performance metrics collection
    
    Example:
        ```python
        balancer = RoundRobinLoadBalancer()
        
        # Add GPU instances
        balancer.add_instance("gpu-1", "192.168.1.100", 8001, gpu_index=0)
        balancer.add_instance("gpu-2", "192.168.1.101", 8001, gpu_index=1)
        
        # Start health checking
        balancer.start_health_checks(interval=10, timeout=5)
        
        # Get next instance for a camera stream
        instance = balancer.get_next_instance()
        request_url = f"{instance.url}/api/detect"
        
        # Track request results
        start_time = time.time()
        try:
            response = requests.post(request_url, data=frame_data)
            duration_ms = (time.time() - start_time) * 1000
            balancer.record_request_success(instance.instance_id, duration_ms)
        except Exception as e:
            balancer.record_request_failure(instance.instance_id)
        ```
    """
    
    def __init__(self, max_consecutive_failures: int = 3, timeout: float = 5.0):
        """
        Initialize load balancer.
        
        Args:
            max_consecutive_failures: Number of failures before marking unhealthy
            timeout: Health check timeout in seconds
        """
        self.instances: Dict[str, GpuInstance] = {}
        self.healthy_instances: List[str] = []
        self.current_index: int = 0
        self.max_consecutive_failures = max_consecutive_failures
        self.timeout = timeout
        
        # Health check thread
        self.health_check_thread: Optional[threading.Thread] = None
        self.health_check_interval: float = 10.0
        self.running: bool = False
        
        # Stream assignments
        self.stream_assignments: Dict[str, str] = {}  # camera_id -> instance_id
        
        logger.info("RoundRobinLoadBalancer initialized")
    
    def add_instance(self, instance_id: str, host: str, port: int, gpu_index: int = 0) -> None:
        """
        Add a GPU instance to the load balancer.
        
        Args:
            instance_id: Unique instance identifier
            host: Instance hostname/IP
            port: Instance port
            gpu_index: GPU index on the instance
        """
        if instance_id in self.instances:
            logger.warning(f"Instance {instance_id} already exists, skipping")
            return
        
        instance = GpuInstance(
            instance_id=instance_id,
            host=host,
            port=port,
            gpu_index=gpu_index
        )
        
        self.instances[instance_id] = instance
        self.healthy_instances.append(instance_id)
        
        logger.info(f"Added instance: {instance_id} at {host}:{port} (GPU {gpu_index})")
    
    def remove_instance(self, instance_id: str) -> None:
        """Remove an instance from load balancer."""
        if instance_id in self.instances:
            del self.instances[instance_id]
            if instance_id in self.healthy_instances:
                self.healthy_instances.remove(instance_id)
            if instance_id in self.stream_assignments.values():
                # Reassign streams
                for camera_id in list(self.stream_assignments.keys()):
                    if self.stream_assignments[camera_id] == instance_id:
                        del self.stream_assignments[camera_id]
            
            logger.info(f"Removed instance: {instance_id}")
    
    def get_next_instance(self) -> Optional[GpuInstance]:
        """
        Get next healthy instance using round-robin selection.
        
        Returns:
            GpuInstance if available, None if no healthy instances
        """
        if not self.healthy_instances:
            logger.warning("No healthy instances available")
            return None
        
        # Round-robin selection
        instance_id = self.healthy_instances[self.current_index % len(self.healthy_instances)]
        self.current_index += 1
        
        return self.instances[instance_id]
    
    def get_instance_for_stream(self, camera_id: str) -> Optional[GpuInstance]:
        """
        Get or assign instance for a specific camera stream.
        
        Sticky assignment: same camera always goes to same instance for consistency.
        
        Args:
            camera_id: Camera identifier
            
        Returns:
            GpuInstance if available, None otherwise
        """
        # Return existing assignment
        if camera_id in self.stream_assignments:
            instance_id = self.stream_assignments[camera_id]
            if instance_id in self.healthy_instances:
                return self.instances[instance_id]
            else:
                # Previously assigned instance is now unhealthy
                del self.stream_assignments[camera_id]
        
        # Assign new instance
        instance = self.get_next_instance()
        if instance:
            self.stream_assignments[camera_id] = instance.instance_id
            logger.info(f"Assigned camera {camera_id} to instance {instance.instance_id}")
        
        return instance
    
    def start_health_checks(self, interval: float = 10.0, timeout: float = 5.0) -> None:
        """
        Start background health checking.
        
        Args:
            interval: Check interval in seconds
            timeout: Request timeout in seconds
        """
        self.health_check_interval = interval
        self.timeout = timeout
        
        if self.running:
            logger.warning("Health checks already running")
            return
        
        self.running = True
        self.health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self.health_check_thread.start()
        
        logger.info(f"Health checks started (interval: {interval}s, timeout: {timeout}s)")
    
    def stop_health_checks(self) -> None:
        """Stop background health checking."""
        self.running = False
        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)
        logger.info("Health checks stopped")
    
    def _health_check_loop(self) -> None:
        """Background health check loop."""
        while self.running:
            try:
                for instance_id in list(self.instances.keys()):
                    self._check_instance_health(instance_id)
                time.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(1)
    
    def _check_instance_health(self, instance_id: str) -> bool:
        """
        Check health of a single instance.
        
        Args:
            instance_id: Instance to check
            
        Returns:
            True if healthy, False otherwise
        """
        instance = self.instances.get(instance_id)
        if not instance:
            return False
        
        try:
            start_time = time.time()
            response = requests.get(
                instance.health_endpoint,
                timeout=self.timeout
            )
            duration_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                # Healthy
                instance.status = InstanceStatus.HEALTHY
                instance.last_health_check = datetime.now()
                instance.consecutive_failures = 0
                instance.record_response_time(duration_ms)
                
                # Re-add to healthy list if it was removed
                if instance_id not in self.healthy_instances:
                    self.healthy_instances.append(instance_id)
                    logger.info(f"Instance {instance_id} recovered (healthy)")
                
                return True
            else:
                # Unhealthy response code
                instance.consecutive_failures += 1
                instance.status = InstanceStatus.UNHEALTHY
                instance.last_health_check = datetime.now()
                
        except requests.Timeout:
            instance.consecutive_failures += 1
            instance.status = InstanceStatus.UNHEALTHY
            instance.last_health_check = datetime.now()
            
        except Exception as e:
            instance.consecutive_failures += 1
            instance.status = InstanceStatus.UNHEALTHY
            instance.last_health_check = datetime.now()
        
        # Mark unhealthy if exceeded failure threshold
        if instance.consecutive_failures >= self.max_consecutive_failures:
            if instance_id in self.healthy_instances:
                self.healthy_instances.remove(instance_id)
                logger.warning(
                    f"Instance {instance_id} marked unhealthy "
                    f"({instance.consecutive_failures} consecutive failures)"
                )
        
        return False
    
    def record_request_success(self, instance_id: str, duration_ms: float) -> None:
        """
        Record successful request to an instance.
        
        Args:
            instance_id: Instance that handled request
            duration_ms: Request duration in milliseconds
        """
        instance = self.instances.get(instance_id)
        if instance:
            instance.record_success()
            instance.record_response_time(duration_ms)
    
    def record_request_failure(self, instance_id: str) -> None:
        """
        Record failed request to an instance.
        
        Args:
            instance_id: Instance that failed request
        """
        instance = self.instances.get(instance_id)
        if instance:
            instance.record_failure()
    
    def get_statistics(self) -> Dict:
        """
        Get load balancer statistics.
        
        Returns:
            Dictionary with overall and per-instance statistics
        """
        return {
            'total_instances': len(self.instances),
            'healthy_instances': len(self.healthy_instances),
            'active_stream_assignments': len(self.stream_assignments),
            'instances': {
                instance_id: instance.to_dict()
                for instance_id, instance in self.instances.items()
            },
            'stream_assignments': self.stream_assignments,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_instance_status(self, instance_id: str) -> Optional[Dict]:
        """Get status of a specific instance."""
        instance = self.instances.get(instance_id)
        if instance:
            return instance.to_dict()
        return None
    
    def get_health_summary(self) -> Dict:
        """Get summary of system health."""
        total = len(self.instances)
        healthy = len(self.healthy_instances)
        
        return {
            'total_instances': total,
            'healthy_instances': healthy,
            'unhealthy_instances': total - healthy,
            'health_percentage': (healthy / total * 100) if total > 0 else 0,
            'avg_response_time_ms': self._calculate_avg_response_time(),
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_avg_response_time(self) -> float:
        """Calculate average response time across all instances."""
        response_times = []
        for instance in self.instances.values():
            if instance.response_times:
                response_times.extend(instance.response_times)
        
        if response_times:
            return sum(response_times) / len(response_times)
        return 0.0
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"RoundRobinLoadBalancer("
            f"total_instances={len(self.instances)}, "
            f"healthy={len(self.healthy_instances)})"
        )
