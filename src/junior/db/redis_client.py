"""Redis client wrapper for caching and job queue management.

Provides:
- Connection pooling
- Health checks
- TTL management
- Key namespace isolation
"""

import json
import hashlib
from typing import Any, Optional
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError, ConnectionError

from junior.core import get_logger, settings

logger = get_logger(__name__)


class RedisClient:
    """Singleton Redis client with connection pooling and health checks."""

    _instance: Optional["RedisClient"] = None
    _redis: Optional[Redis] = None
    _pool: Optional[ConnectionPool] = None

    def __new__(cls) -> "RedisClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "RedisClient":
        """Get or create Redis client instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def _ensure_connected(self) -> Redis:
        """Ensure Redis connection is established."""
        if self._redis is None:
            if not settings.redis_enabled:
                raise RuntimeError("Redis is disabled in settings")

            try:
                self._redis = redis.from_url(
                    settings.redis_url,
                    db=settings.redis_db,
                    password=settings.redis_password if settings.redis_password else None,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                    retry_on_timeout=True,
                )
                # Test connection
                await self._redis.ping()
                logger.info("✅ Redis connected successfully")
            except (RedisError, ConnectionError) as e:
                logger.error(f"❌ Redis connection failed: {e}")
                self._redis = None
                raise

        return self._redis

    async def connect(self) -> None:
        """Initialize Redis connection."""
        if not settings.redis_enabled:
            logger.warning("⚠️  Redis is disabled")
            return

        try:
            await self._ensure_connected()
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis connection closed")

    async def health_check(self) -> bool:
        """Check if Redis is healthy."""
        try:
            if not settings.redis_enabled:
                return False

            redis_client = await self._ensure_connected()
            await redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: str = "junior",
    ) -> bool:
        """Set a value in Redis with optional TTL.

        Args:
            key: Redis key
            value: Value to store (will be JSON-serialized)
            ttl: Time-to-live in seconds (None = no expiration)
            namespace: Key namespace prefix

        Returns:
            True if set successfully
        """
        if not settings.redis_enabled:
            return False

        try:
            redis_client = await self._ensure_connected()
            full_key = f"{namespace}:{key}"
            serialized_value = json.dumps(value) if not isinstance(value, str) else value

            if ttl:
                await redis_client.setex(full_key, ttl, serialized_value)
            else:
                await redis_client.set(full_key, serialized_value)

            logger.debug(f"Cache SET: {full_key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache SET failed for {key}: {e}")
            return False

    async def get(
        self,
        key: str,
        namespace: str = "junior",
        default: Any = None,
    ) -> Any:
        """Get a value from Redis.

        Args:
            key: Redis key
            namespace: Key namespace prefix
            default: Default value if key not found

        Returns:
            Cached value or default
        """
        if not settings.redis_enabled:
            return default

        try:
            redis_client = await self._ensure_connected()
            full_key = f"{namespace}:{key}"
            value = await redis_client.get(full_key)

            if value is None:
                logger.debug(f"Cache MISS: {full_key}")
                return default

            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            logger.error(f"Cache GET failed for {key}: {e}")
            return default

    async def delete(self, key: str, namespace: str = "junior") -> bool:
        """Delete a key from Redis.

        Args:
            key: Redis key
            namespace: Key namespace prefix

        Returns:
            True if key was deleted
        """
        if not settings.redis_enabled:
            return False

        try:
            redis_client = await self._ensure_connected()
            full_key = f"{namespace}:{key}"
            result = await redis_client.delete(full_key)
            logger.debug(f"Cache DELETE: {full_key} (deleted: {result})")
            return result > 0
        except Exception as e:
            logger.error(f"Cache DELETE failed for {key}: {e}")
            return False

    async def exists(self, key: str, namespace: str = "junior") -> bool:
        """Check if a key exists in Redis."""
        if not settings.redis_enabled:
            return False

        try:
            redis_client = await self._ensure_connected()
            full_key = f"{namespace}:{key}"
            return await redis_client.exists(full_key) > 0
        except Exception as e:
            logger.error(f"Cache EXISTS check failed for {key}: {e}")
            return False

    async def clear_namespace(self, namespace: str = "junior") -> int:
        """Clear all keys in a namespace.

        Args:
            namespace: Key namespace prefix

        Returns:
            Number of keys deleted
        """
        if not settings.redis_enabled:
            return 0

        try:
            redis_client = await self._ensure_connected()
            pattern = f"{namespace}:*"
            keys = await redis_client.keys(pattern)
            if not keys:
                return 0

            deleted = await redis_client.delete(*keys)
            logger.info(f"Cleared {deleted} keys from namespace: {namespace}")
            return deleted
        except Exception as e:
            logger.error(f"Failed to clear namespace {namespace}: {e}")
            return 0

    async def flush_all(self) -> bool:
        """Flush all data from Redis (use with caution!)."""
        if not settings.redis_enabled:
            return False

        try:
            redis_client = await self._ensure_connected()
            await redis_client.flushall()
            logger.warning("⚠️  Redis FLUSH ALL executed")
            return True
        except Exception as e:
            logger.error(f"Failed to flush Redis: {e}")
            return False

    @staticmethod
    def make_cache_key(
        prefix: str,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        """Create a cache key from prefix and arguments.

        Useful for function result caching.

        Args:
            prefix: Key prefix (e.g., "wall:analyze")
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Cache key string
        """
        key_data = f"{prefix}:{args}:{kwargs}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{prefix}:{key_hash}"


async def get_redis_client() -> RedisClient:
    """Get Redis client instance."""
    return RedisClient.get_instance()


def sync_redis_get(key: str, namespace: str = "junior", default: Any = None) -> Any:
    """Synchronous wrapper for Redis GET (for non-async contexts)."""
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Can't use async in running loop
            return default
        return loop.run_until_complete(
            get_redis_client().then(lambda client: client.get(key, namespace, default))
        )
    except Exception as e:
        logger.error(f"Sync Redis GET failed: {e}")
        return default
