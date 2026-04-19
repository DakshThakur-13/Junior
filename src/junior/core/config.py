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
        # Keep class defaults deterministic. Environment loading is applied in
        # get_settings() via explicit _env_file override.
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Junior"
    app_version: str = "0.1.0"
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = True
    # Secret key for session encryption, JWT tokens, CSRF protection
    # MUST be changed in production! Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    app_secret_key: str = Field(default="change-me-in-production")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Groq API
    groq_api_key: str = Field(default="")

    # Perplexity AI (Sonar-Pro)
    perplexity_api_key: str = Field(default="")

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

    # Redis Configuration (for caching, job queue, session management)
    redis_enabled: bool = True
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_db: int = 0
    redis_password: str = Field(default="")
    redis_cache_ttl: int = 3600  # 1 hour
    redis_wall_cache_ttl: int = 1800  # 30 minutes
    redis_suggestion_cache_ttl: int = 900  # 15 minutes

    # Celery Configuration
    celery_broker_url: str = Field(default="redis://localhost:6379/0")
    celery_result_backend: str = Field(default="redis://localhost:6379/0")

    # AI Models - Multi-Model Architecture
    # Legacy default (kept for backward compatibility)
    default_llm_model: str = "llama-3.3-70b-versatile"
    
    # Specialized Models for Each Agent
    researcher_model: str = "sonar-pro"  # Perplexity - 127k context + online search
    researcher_provider: str = "perplexity"  # perplexity | groq | huggingface
    
    critic_model: str = "llama-3.3-70b-versatile"  # Groq - Fast reasoning
    critic_provider: str = "groq"
    
    writer_model: str = "llama-3.3-70b-versatile"  # Groq - Best instruction following
    writer_provider: str = "groq"
    
    chat_model: str = "sonar-pro"  # Perplexity - 127k context + online search
    chat_provider: str = "perplexity"
    
    # Reasoning model (for DeepSeek-R1 when available)
    reasoning_model: str = "llama-3.3-70b-versatile"
    
    # Embeddings - Upgraded to multilingual
    embedding_model: str = "BAAI/bge-m3"  # Multilingual + Hybrid search
    embedding_dimension: int = 1024
    reranker_model: str = "BAAI/bge-reranker-v2-m3"  # Precision boost

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

    # Admin API
    admin_api_key: str = Field(default="")

    # Translation
    default_source_lang: str = "en"
    supported_languages: str = "en,hi,mr,ta,te,bn,gu,kn,ml,pa"

    # Audio / Voice-to-Brief
    whisper_model_size: str = "base"  # tiny|base|small|medium|large-v3 (depends on faster-whisper availability)
    audio_max_bytes: int = 25_000_000

    # Indian Kanoon API (free for research use)
    # Get your key at: https://api.indiankanoon.org/
    indian_kanoon_api_key: str = Field(default="")

    # OpenRouter API — access 100+ models via OpenAI-compatible API
    # Get a free key at: https://openrouter.ai/keys
    openrouter_api_key: str = Field(default="")

    # Translator model/provider (used by ModelRouter for TRANSLATOR purpose)
    translator_model: str = Field(default="qwen/qwen-2.5-72b-instruct")
    translator_provider: str = Field(default="openrouter")

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
    return Settings(_env_file=(str(_ENV_FILE), ".env"))

# Global settings instance
settings = get_settings()
