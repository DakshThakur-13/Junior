"""
Database module for Junior
Handles Supabase connection and repositories
"""

from .client import get_supabase_client, SupabaseClient
from .repositories import DocumentRepository, ChatRepository, UserRepository

__all__ = [
    "get_supabase_client",
    "SupabaseClient",
    "DocumentRepository",
    "ChatRepository",
    "UserRepository",
]
