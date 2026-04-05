"""
Redis Caching Layer for Analytics Data

Implements distributed caching with automatic invalidation for frequently
accessed traffic analytics data. Supports fallback to in-memory cache and
multiple cache strategies.

Features:
- Redis connection with automatic fallback
- TTL-based cache expiration
- Automatic invalidation on detection updates
- Per-lane and global cache keys
- In-memory fallback for resilience
- Cache warming and preloading
- Hit/miss statistics

Author: Traffic Intelligence Team
Version: 1.0.0
"""

import json
import logging
import hashlib
import time
from typing import Any, Dict, Optional, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from collections import deque

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("redis package not installed, using in-memory cache fallback")

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    invalidations: int = 0
    errors: int = 0
    last_hit: Optional[datetime] = None
    last_miss: Optional[datetime] = None
    
    @property
    def hit_rate(self) -> float:
        """Calculate hit rate percentage."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return (self.hits / total) * 100
    
    @property
    def total_accesses(self) -> int:
        """Total cache accesses."""
        return self.hits + self.misses
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'invalidations': self.invalidations,
            'errors': self.errors,
            'hit_rate': f"{self.hit_rate:.2f}%",
            'total_accesses': self.total_accesses,
            'last_hit': self.last_hit.isoformat() if self.last_hit else None,
            'last_miss': self.last_miss.isoformat() if self.last_miss else None
        }


class RedisCache:
    """
    Redis-backed cache with automatic fallback to in-memory cache.
    
    Features:
    - Transparent Redis integration
    - In-memory cache fallback if Redis unavailable
    - TTL management
    - Automatic cache invalidation patterns
    - Performance statistics
    
    Example:
        ```python
        cache = RedisCache(
            host='localhost',
            port=6379,
            ttl=300,  # 5 minutes
            fallback_enabled=True
        )
        
        # Cache traffic data
        cache.set('traffic:north:current', traffic_data, ttl=60)
        
        # Retrieve cached data
        data = cache.get('traffic:north:current')
        
        # Invalidate on detection
        cache.invalidate_pattern('traffic:*')
        
        # Get statistics
        stats = cache.get_stats()
        ```
    """
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        ttl: int = 300,
        fallback_enabled: bool = True,
        max_fallback_size: int = 1000
    ):
        """
        Initialize Redis cache.
        
        Args:
            host: Redis server hostname
            port: Redis server port
            db: Redis database index
            ttl: Default TTL in seconds
            fallback_enabled: Enable in-memory fallback
            max_fallback_size: Max entries in fallback cache
        """
        self.host = host
        self.port = port
        self.db = db
        self.ttl = ttl
        self.fallback_enabled = fallback_enabled
        self.max_fallback_size = max_fallback_size
        
        # Try to connect to Redis
        self.redis_client: Optional[redis.Redis] = None
        self.using_fallback: bool = False
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True
                )
                # Test connection
                self.redis_client.ping()
                logger.info(f"Connected to Redis at {host}:{port}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                self.redis_client = None
                self.using_fallback = True
        else:
            logger.warning("redis package not installed, using in-memory fallback")
            self.using_fallback = True
        
        # Fallback in-memory cache
        self.memory_cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
        self.memory_lru: deque = deque(maxlen=max_fallback_size)
        
        # Statistics
        self.stats = CacheStats()
        
        logger.info(f"RedisCache initialized (using_fallback={self.using_fallback})")
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a cache value.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: TTL in seconds (uses default if None)
            
        Returns:
            True if successful, False otherwise
        """
        if ttl is None:
            ttl = self.ttl
        
        try:
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value)
            else:
                serialized = str(value)
            
            # Try Redis first
            if self.redis_client:
                try:
                    self.redis_client.setex(key, ttl, serialized)
                    logger.debug(f"Redis SET: {key} (ttl={ttl}s)")
                    return True
                except Exception as e:
                    logger.error(f"Redis SET failed for {key}: {e}")
                    self.stats.errors += 1
                    if not self.fallback_enabled:
                        return False
            
            # Fallback to memory cache
            expiry_time = time.time() + ttl
            self.memory_cache[key] = (serialized, expiry_time)
            self.memory_lru.append(key)
            
            logger.debug(f"Memory SET: {key} (ttl={ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Cache SET error: {e}")
            self.stats.errors += 1
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a cached value.
        
        Args:
            key: Cache key
            
        Returns:
            Deserialized value if found, None otherwise
        """
        try:
            # Try Redis first
            if self.redis_client:
                try:
                    value = self.redis_client.get(key)
                    if value is not None:
                        logger.debug(f"Redis HIT: {key}")
                        self.stats.hits += 1
                        self.stats.last_hit = datetime.now()
                        
                        # Try to deserialize
                        return self._deserialize(value)
                    else:
                        logger.debug(f"Redis MISS: {key}")
                        self.stats.misses += 1
                        self.stats.last_miss = datetime.now()
                        return None
                except Exception as e:
                    logger.error(f"Redis GET failed for {key}: {e}")
                    self.stats.errors += 1
            
            # Fallback to memory cache
            if key in self.memory_cache:
                value, expiry_time = self.memory_cache[key]
                
                # Check expiry
                if time.time() < expiry_time:
                    logger.debug(f"Memory HIT: {key}")
                    self.stats.hits += 1
                    self.stats.last_hit = datetime.now()
                    return self._deserialize(value)
                else:
                    # Expired, remove
                    del self.memory_cache[key]
                    logger.debug(f"Memory EXPIRED: {key}")
            
            logger.debug(f"Cache MISS: {key}")
            self.stats.misses += 1
            self.stats.last_miss = datetime.now()
            return None
            
        except Exception as e:
            logger.error(f"Cache GET error: {e}")
            self.stats.errors += 1
            return None
    
    def delete(self, key: str) -> bool:
        """Delete a cache entry."""
        try:
            deleted = False
            
            # Delete from Redis
            if self.redis_client:
                try:
                    self.redis_client.delete(key)
                    deleted = True
                except Exception as e:
                    logger.error(f"Redis DELETE failed for {key}: {e}")
            
            # Delete from memory cache
            if key in self.memory_cache:
                del self.memory_cache[key]
                deleted = True
            
            if deleted:
                logger.debug(f"Cache DELETE: {key}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Cache DELETE error: {e}")
            self.stats.errors += 1
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching a pattern.
        
        Args:
            pattern: String pattern (e.g., 'traffic:north:*')
            
        Returns:
            Number of keys invalidated
        """
        try:
            count = 0
            
            # Invalidate in Redis
            if self.redis_client:
                try:
                    cursor = 0
                    while True:
                        cursor, keys = self.redis_client.scan(cursor, match=pattern)
                        for key in keys:
                            self.redis_client.delete(key)
                            count += 1
                        if cursor == 0:
                            break
                except Exception as e:
                    logger.error(f"Redis pattern invalidation failed: {e}")
            
            # Invalidate in memory cache
            keys_to_delete = []
            for key in self.memory_cache.keys():
                if self._match_pattern(key, pattern):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self.memory_cache[key]
                count += 1
            
            self.stats.invalidations += count
            logger.info(f"Invalidated {count} cache entries matching pattern: {pattern}")
            return count
            
        except Exception as e:
            logger.error(f"Pattern invalidation error: {e}")
            self.stats.errors += 1
            return 0
    
    def clear(self) -> bool:
        """Clear entire cache."""
        try:
            # Clear Redis
            if self.redis_client:
                try:
                    self.redis_client.flushdb()
                except Exception as e:
                    logger.error(f"Redis FLUSHDB failed: {e}")
            
            # Clear memory cache
            self.memory_cache.clear()
            
            logger.info("Cache cleared")
            return True
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            self.stats.errors += 1
            return False
    
    def _deserialize(self, value: str) -> Any:
        """Deserialize cached JSON value."""
        try:
            # Try JSON deserialization
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            # Return as string if not JSON
            return value
    
    @staticmethod
    def _match_pattern(key: str, pattern: str) -> bool:
        """Simple pattern matching (supports * wildcard)."""
        import fnmatch
        return fnmatch.fnmatch(key, pattern)
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        return {
            'cache_type': 'redis' if self.redis_client else 'memory',
            'redis_available': REDIS_AVAILABLE,
            'using_fallback': self.using_fallback,
            'stats': self.stats.to_dict(),
            'memory_cache_size': len(self.memory_cache),
            'timestamp': datetime.now().isoformat()
        }
    
    def is_available(self) -> bool:
        """Check if cache is available."""
        if self.redis_client:
            try:
                self.redis_client.ping()
                return True
            except:
                return False
        return self.fallback_enabled
    
    def __repr__(self) -> str:
        """String representation."""
        cache_type = 'redis' if self.redis_client else 'memory'
        return f"RedisCache({cache_type}, size={len(self.memory_cache)})"


class CacheManager:
    """
    High-level cache manager for traffic analytics.
    
    Manages cache keys, patterns, and automatic invalidation strategies.
    """
    
    # Cache key templates
    KEYS = {
        'current_status': 'traffic:status:current',
        'lane_status': 'traffic:status:lane:{lane}',
        'hourly_stats': 'traffic:stats:hourly:{date}:{hour}',
        'daily_stats': 'traffic:stats:daily:{date}',
        'violations': 'traffic:violations:{date}',
        'violations_lane': 'traffic:violations:{lane}:{date}',
        'peak_hours': 'traffic:analysis:peak-hours',
        'vehicle_counts': 'traffic:counts:lane:{lane}',
        'wait_times': 'traffic:wait-times:lane:{lane}',
        'congestion_prediction': 'traffic:prediction:congestion:{lane}',
        'anomalies': 'traffic:anomalies:lane:{lane}',
        'signal_state': 'traffic:signal:{lane}',
    }
    
    def __init__(self, redis_cache: Optional[RedisCache] = None):
        """Initialize cache manager."""
        self.cache = redis_cache or RedisCache()
        logger.info("CacheManager initialized")
    
    def cache_lane_status(self, lane: str, data: Dict, ttl: int = 30) -> bool:
        """Cache current lane status."""
        key = self.KEYS['lane_status'].format(lane=lane)
        return self.cache.set(key, data, ttl)
    
    def get_lane_status(self, lane: str) -> Optional[Dict]:
        """Get cached lane status."""
        key = self.KEYS['lane_status'].format(lane=lane)
        return self.cache.get(key)
    
    def cache_hourly_stats(self, date: str, hour: int, data: Dict, ttl: int = 3600) -> bool:
        """Cache hourly statistics."""
        key = self.KEYS['hourly_stats'].format(date=date, hour=hour)
        return self.cache.set(key, data, ttl)
    
    def get_hourly_stats(self, date: str, hour: int) -> Optional[Dict]:
        """Get cached hourly statistics."""
        key = self.KEYS['hourly_stats'].format(date=date, hour=hour)
        return self.cache.get(key)
    
    def cache_daily_stats(self, date: str, data: Dict, ttl: int = 86400) -> bool:
        """Cache daily statistics."""
        key = self.KEYS['daily_stats'].format(date=date)
        return self.cache.set(key, data, ttl)
    
    def get_daily_stats(self, date: str) -> Optional[Dict]:
        """Get cached daily statistics."""
        key = self.KEYS['daily_stats'].format(date=date)
        return self.cache.get(key)
    
    def cache_congestion_prediction(self, lane: str, data: Dict, ttl: int = 60) -> bool:
        """Cache congestion prediction."""
        key = self.KEYS['congestion_prediction'].format(lane=lane)
        return self.cache.set(key, data, ttl)
    
    def get_congestion_prediction(self, lane: str) -> Optional[Dict]:
        """Get cached congestion prediction."""
        key = self.KEYS['congestion_prediction'].format(lane=lane)
        return self.cache.get(key)
    
    def invalidate_on_detection(self, lane: str) -> int:
        """
        Invalidate all lane-related caches on new detection.
        
        Args:
            lane: Lane that had detection
            
        Returns:
            Number of keys invalidated
        """
        patterns = [
            self.KEYS['lane_status'].format(lane=lane),
            self.KEYS['vehicle_counts'].format(lane=lane),
            self.KEYS['anomalies'].format(lane=lane),
            self.KEYS['congestion_prediction'].format(lane=lane),
            self.KEYS['violations_lane'].format(lane='*'),
        ]
        
        total_invalidated = 0
        for pattern in patterns:
            self.cache.invalidate_pattern(pattern)
        
        logger.debug(f"Invalidated cache for lane: {lane}")
        return total_invalidated
    
    def invalidate_analytics(self) -> int:
        """Invalidate all analytics caches."""
        return self.cache.invalidate_pattern('traffic:*')
    
    def get_cache_status(self) -> Dict:
        """Get overall cache status."""
        return self.cache.get_stats()


def cached(ttl: int = 300, key_func=None):
    """
    Decorator for caching function results.
    
    Example:
        ```python
        @cached(ttl=300)
        def get_traffic_summary():
            return compute_summary()
        ```
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # Auto-generate key from function name and args
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args if arg is not None)
                key_parts.extend(f"{k}:{v}" for k, v in kwargs.items() if v is not None)
                key = ":".join(key_parts)
            
            # Try to get from cache
            from src.utils.cache_manager import CacheManager
            cache = CacheManager()
            result = cache.cache.get(key)
            
            if result is not None:
                logger.debug(f"Cache HIT for {func.__name__}")
                return result
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            cache.cache.set(key, result, ttl)
            
            return result
        
        return wrapper
    
    return decorator
