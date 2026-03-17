"""Supabase client configuration and health checks."""

from functools import lru_cache
from typing import Any, Optional, TYPE_CHECKING, cast

try:
    from supabase import create_client  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    create_client = None  # type: ignore

if TYPE_CHECKING:
    from supabase import Client as SupabaseSDKClient
else:
    SupabaseSDKClient = Any

from junior.core import settings, get_logger

logger = get_logger(__name__)

class SupabaseClient:
    """Wrapper for Supabase clients with explicit backend-safe behavior."""

    def __init__(self):
        self._public_client: Optional[SupabaseSDKClient] = None
        self._service_client: Optional[SupabaseSDKClient] = None

    @property
    def is_configured(self) -> bool:
        return bool(settings.supabase_url and settings.supabase_key)

    @property
    def has_service_role(self) -> bool:
        return bool(settings.supabase_url and settings.supabase_service_key)

    def _ensure_sdk(self) -> None:
        if create_client is None:
            raise RuntimeError(
                "Supabase is not installed. Install with `pip install supabase` or remove Supabase features."
            )

    def _normalize_url(self) -> str:
        url = (settings.supabase_url or "").strip()
        if not url:
            raise ValueError("Supabase URL must be configured")
        return url.rstrip("/")

    def _build_client(self, key: str) -> SupabaseSDKClient:
        self._ensure_sdk()
        factory = cast(Any, create_client)
        return factory(self._normalize_url(), key)

    @property
    def public_client(self) -> SupabaseSDKClient:
        if self._public_client is None:
            if not self.is_configured:
                logger.warning("Supabase public credentials not configured")
                raise ValueError("Supabase URL and Key must be configured")
            self._public_client = self._build_client(settings.supabase_key)
        return self._public_client

    @property
    def client(self) -> SupabaseSDKClient:
        """Backend-facing client; prefer service role when available."""
        if self.has_service_role:
            return self.get_service_client()
        return self.public_client

    def get_service_client(self) -> SupabaseSDKClient:
        """Get Supabase client with service role key (bypasses RLS)."""
        self._ensure_sdk()
        if not self.has_service_role:
            raise ValueError("Supabase service credentials not configured")
        if self._service_client is None:
            self._service_client = self._build_client(settings.supabase_service_key)
            logger.info("Supabase client initialized (service_role)")
        return self._service_client

    def healthcheck(self) -> dict[str, Any]:
        """Perform a lightweight connectivity probe for operational health."""
        if not self.is_configured:
            return {
                "ok": False,
                "configured": False,
                "mode": "none",
                "message": "Supabase URL/key not configured",
            }

        mode = "service_role" if self.has_service_role else "anon"
        try:
            probe = self.client.table("documents").select("id").limit(1).execute()
            return {
                "ok": True,
                "configured": True,
                "mode": mode,
                "message": "Supabase reachable",
                "row_count_available": getattr(probe, "count", None) is not None,
            }
        except Exception as exc:
            logger.warning(f"Supabase health check failed: {exc}")
            return {
                "ok": False,
                "configured": True,
                "mode": mode,
                "message": str(exc),
            }

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
