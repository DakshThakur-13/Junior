"""Decorators for Redis-based caching.

Provides:
- Async function result caching
- Automatic TTL management
- Cache invalidation patterns
"""

import functools
import inspect
from typing import Any, Callable, Optional

from junior.core import get_logger
from junior.db.redis_client import get_redis_client, RedisClient

logger = get_logger(__name__)


def redis_cache(
    key_prefix: str,
    ttl: Optional[int] = None,
    namespace: str = "junior",
):
    """Decorator for caching async function results in Redis.

    Args:
        key_prefix: Prefix for cache key
        ttl: Time-to-live in seconds
        namespace: Redis namespace

    Usage:
        @redis_cache(key_prefix="wall:analyze", ttl=1800)
        async def analyze_wall(case_id: str, nodes: list):
            return result

        # Cache key will be: junior:wall:analyze:<hash of args>
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not inspect.iscoroutinefunction(func):
                raise TypeError(f"{func.__name__} must be async")

            # Create cache key
            cache_key = RedisClient.make_cache_key(key_prefix, *args, **kwargs)

            # Try to get from cache
            try:
                redis_client = await get_redis_client()
                cached = await redis_client.get(cache_key, namespace=namespace)
                if cached is not None:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return cached
                logger.debug(f"Cache MISS: {cache_key}")
            except Exception as e:
                logger.warning(f"Cache lookup failed: {e}")

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            try:
                redis_client = await get_redis_client()
                await redis_client.set(cache_key, result, ttl=ttl, namespace=namespace)
            except Exception as e:
                logger.warning(f"Failed to cache result: {e}")

            return result

        return wrapper

    return decorator


def redis_cache_with_invalidation(
    key_prefix: str,
    ttl: Optional[int] = None,
    namespace: str = "junior",
    invalidate_keys: Optional[list[str]] = None,
):
    """Decorator with manual cache invalidation support.

    Args:
        key_prefix: Prefix for cache key
        ttl: Time-to-live in seconds
        namespace: Redis namespace
        invalidate_keys: List of cache keys to invalidate after execution

    Usage:
        @redis_cache_with_invalidation(
            key_prefix="wall:save",
            invalidate_keys=["wall:list:*"]
        )
        async def save_wall_snapshot(case_id, snapshot):
            # ... save logic ...
            return result
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Execute function
            result = await func(*args, **kwargs)

            # Invalidate specified cache keys
            if invalidate_keys:
                try:
                    redis_client = await get_redis_client()
                    for key_pattern in invalidate_keys:
                        # Simple pattern support (for now just exact keys)
                        await redis_client.delete(key_pattern, namespace=namespace)
                except Exception as e:
                    logger.warning(f"Cache invalidation failed: {e}")

            return result

        return wrapper

    return decorator
