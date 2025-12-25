"""
Supabase client configuration
"""

from functools import lru_cache
from typing import Any, Optional

try:
    from supabase import Client, create_client  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    Client = Any  # type: ignore
    create_client = None  # type: ignore

from junior.core import settings, get_logger

logger = get_logger(__name__)

class SupabaseClient:
    """Wrapper for Supabase client with connection management"""

    _instance: Optional[Client] = None

    def __init__(self):
        self._client: Optional[Client] = None

    @property
    def client(self) -> Client:
        """Get or create Supabase client"""
        if self._client is None:
            if create_client is None:
                raise RuntimeError(
                    "Supabase is not installed. Install with `pip install supabase` or remove Supabase features."
                )
            if not settings.supabase_url or not settings.supabase_key:
                logger.warning("Supabase credentials not configured")
                raise ValueError("Supabase URL and Key must be configured")

            # Prefer service role key on the backend if present.
            # This avoids "empty results" caused by RLS policies when using the anon key.
            key = settings.supabase_service_key or settings.supabase_key
            self._client = create_client(settings.supabase_url, key)
            logger.info(
                "Supabase client initialized (%s)"
                % ("service_role" if settings.supabase_service_key else "anon")
            )

        return self._client

    def get_service_client(self) -> Client:
        """Get Supabase client with service role key (bypasses RLS)"""
        if create_client is None:
            raise RuntimeError(
                "Supabase is not installed. Install with `pip install supabase` or remove Supabase features."
            )
        if not settings.supabase_url or not settings.supabase_service_key:
            raise ValueError("Supabase service credentials not configured")

        return create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )

    # Table shortcuts
    @property
    def documents(self):
        """Access documents table"""
        return self.client.table("documents")

    @property
    def document_chunks(self):
        """Access document_chunks table"""
        return self.client.table("document_chunks")

    @property
    def chat_sessions(self):
        """Access chat_sessions table"""
        return self.client.table("chat_sessions")

    @property
    def chat_messages(self):
        """Access chat_messages table"""
        return self.client.table("chat_messages")

    @property
    def users(self):
        """Access users table"""
        return self.client.table("users")

    @property
    def citations(self):
        """Access citations table"""
        return self.client.table("citations")

@lru_cache
def get_supabase_client() -> SupabaseClient:
    """Get cached Supabase client instance"""
    return SupabaseClient()
