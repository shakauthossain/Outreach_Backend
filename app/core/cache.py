"""Redis caching utilities with tiered TTL strategy."""

import json
from typing import Any, Optional
from functools import wraps
import hashlib

from redis import asyncio as aioredis
from app.config import settings


class CacheManager:
    """Async Redis cache manager with tiered TTL strategy."""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
    
    async def connect(self):
        """Establish Redis connection."""
        self.redis = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not self.redis:
            return None
        
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            print(f"Cache get error: {e}")
        
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (None = no expiration)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis:
            return False
        
        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                await self.redis.setex(key, ttl, serialized)
            else:
                await self.redis.set(key, serialized)
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False otherwise
        """
        if not self.redis:
            return False
        
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Redis key pattern (e.g., "leads:*")
            
        Returns:
            Number of keys deleted
        """
        if not self.redis:
            return 0
        
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            print(f"Cache delete pattern error: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        if not self.redis:
            return False
        
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            print(f"Cache exists error: {e}")
            return False


# Global cache manager instance
cache_manager = CacheManager()


# Cache TTL tiers (in seconds)
class CacheTTL:
    """Standard cache TTL values for different data types."""
    
    # Very short - frequently changing data
    REALTIME = 30  # 30 seconds
    
    # Short - list views, counters
    SHORT = 120  # 2 minutes
    LIST = 300  # 5 minutes
    
    # Medium - individual records
    MEDIUM = 900  # 15 minutes
    DETAIL = 1800  # 30 minutes
    
    # Long - expensive operations
    LONG = 3600  # 1 hour
    SPEEDTEST = 86400  # 24 hours (PageSpeed results)
    SCREENSHOT = 43200  # 12 hours
    
    # Very long - rarely changing data
    STATIC = 604800  # 1 week
    CONFIG = 2592000  # 30 days


def generate_cache_key(*args, prefix: str = "cache") -> str:
    """
    Generate a cache key from arguments.
    
    Args:
        *args: Arguments to include in key
        prefix: Key prefix
        
    Returns:
        Generated cache key
    """
    key_parts = [str(arg) for arg in args]
    key_string = ":".join(key_parts)
    
    # Hash if key is too long
    if len(key_string) > 100:
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{prefix}:{key_hash}"
    
    return f"{prefix}:{key_string}"


def cached(
    ttl: int = CacheTTL.MEDIUM,
    key_prefix: str = "func",
    skip_args: Optional[list[int]] = None,
):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Cache TTL in seconds
        key_prefix: Cache key prefix
        skip_args: List of argument indices to skip in key generation
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [func.__name__]
            
            # Add non-skipped args
            for i, arg in enumerate(args):
                if skip_args and i in skip_args:
                    continue
                # Skip database session objects
                if hasattr(arg, '__class__') and 'session' in arg.__class__.__name__.lower():
                    continue
                key_parts.append(str(arg))
            
            # Add kwargs
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}={v}")
            
            cache_key = generate_cache_key(*key_parts, prefix=key_prefix)
            
            # Try to get from cache
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache_manager.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


# Cache key patterns for invalidation
class CacheKeys:
    """Standard cache key patterns."""
    
    LEAD_LIST = "leads:list:*"
    LEAD_DETAIL = "leads:detail:*"
    LEAD_STATS = "leads:stats"
    
    SPEEDTEST = "speedtest:*"
    SCREENSHOT = "screenshot:*"
    
    USER_DETAIL = "user:*"
    
    MAIL_TEMPLATE = "mail:template:*"
    
    GHL_CONTACT = "ghl:contact:*"
