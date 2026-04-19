"""
Database module for Junior
Handles Supabase connection and repositories, Redis caching
"""

from .client import get_supabase_client, SupabaseClient
from .repositories import DocumentRepository, ChatRepository, UserRepository
from .redis_client import get_redis_client, RedisClient
from .redis_cache import redis_cache, redis_cache_with_invalidation

__all__ = [
    "get_supabase_client",
    "SupabaseClient",
    "DocumentRepository",
    "ChatRepository",
    "UserRepository",
    "get_redis_client",
    "RedisClient",
    "redis_cache",
    "redis_cache_with_invalidation",
]
