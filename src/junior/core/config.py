"""Application configuration using Pydantic Settings.

NOTE: We resolve the `.env` file relative to the repository root so running the
app from different working directories (tests, uvicorn, scripts) doesn't
silently drop configuration.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

def _repo_root() -> Path:
    # config.py -> core/ -> junior/ -> src/ -> repo root
    return Path(__file__).resolve().parents[3]

_ENV_FILE = _repo_root() / ".env"

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        # Prefer repo-root `.env` regardless of current working directory.
        # Keep `.env` as a fallback for unusual run layouts.
        env_file=(str(_ENV_FILE), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Junior"
    app_version: str = "0.1.0"
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = True
    app_secret_key: str = Field(default="change-me-in-production")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Groq API
    groq_api_key: str = Field(default="")

    # Hugging Face API
    huggingface_api_key: str = Field(default="")

    # Mistral API
    mistral_api_key: str = Field(default="")

    # Together AI
    together_api_key: str = Field(default="")

    # Supabase
    supabase_url: str = Field(default="")
    supabase_key: str = Field(default="")
    supabase_service_key: str = Field(default="")

    # AI Models
    default_llm_model: str = "llama-3.3-70b-versatile"
    reasoning_model: str = "deepseek-r1-distill-llama-70b"
    # Free + strong retrieval default (local sentence-transformers)
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    # When false, Junior will NOT attempt to download embedding models from Hugging Face Hub.
    # This avoids very slow retries on networks where huggingface.co is blocked.
    allow_hf_model_downloads: bool = False

    # Manual ingestion (RAG training) settings
    manuals_download_dir: str = "uploads/manuals"
    manuals_max_bytes: int = 50_000_000
    manuals_allow_url_ingest: bool = False
    manuals_allowlist_domains: str = ""

    # Privacy
    enable_pii_redaction: bool = True
    watermark_drafts: bool = True

    # Translation
    default_source_lang: str = "en"
    supported_languages: str = "en,hi,mr,ta,te,bn,gu,kn,ml,pa"

    # Audio / Voice-to-Brief
    whisper_model_size: str = "base"  # tiny|base|small|medium|large-v3 (depends on faster-whisper availability)
    audio_max_bytes: int = 25_000_000

    @property
    def supported_languages_list(self) -> list[str]:
        """Get supported languages as a list"""
        return [lang.strip() for lang in self.supported_languages.split(",")]

    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.app_env == "production"

@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Global settings instance
settings = get_settings()
