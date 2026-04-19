"""
Health check endpoints

Monitors:
- LLM APIs (Groq, OpenRouter)
- Database (Supabase/Postgres)
- Cache (Redis)
- Job Queue (Celery)
- Core services (PII redaction, embeddings)
"""

from datetime import datetime
from fastapi import APIRouter

from junior.core import settings, get_logger
from junior.api.schemas import HealthResponse
from junior.db import get_supabase_client

logger = get_logger(__name__)
router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Comprehensive health check endpoint

    Returns status of all critical and optional services
    """
    services = {}
    degraded_services = []

    # ===== LLM APIs =====
    # Check Groq API
    if settings.groq_api_key:
        services["groq"] = "configured"
    else:
        services["groq"] = "not_configured"
        degraded_services.append("groq")

    # Check OpenRouter API
    if settings.openrouter_api_key:
        services["openrouter"] = "configured"
    else:
        services["openrouter"] = "not_configured"

    # ===== Database =====
    try:
        if settings.supabase_url and settings.supabase_key:
            db_status = get_supabase_client().healthcheck()
            services["supabase"] = "connected" if db_status.get("ok") else f"degraded: {db_status.get('message')}"
            if not db_status.get("ok"):
                degraded_services.append("supabase")
        else:
            services["supabase"] = "not_configured"
            degraded_services.append("supabase")
    except Exception as e:
        services["supabase"] = f"error: {str(e)[:50]}"
        degraded_services.append("supabase")

    # ===== Redis Cache & Queue =====
    try:
        if settings.redis_enabled:
            from junior.db import get_redis_client
            redis_client = await get_redis_client()
            health = await redis_client.health_check()
            services["redis"] = "connected" if health else "disconnected"
            if not health:
                degraded_services.append("redis")
        else:
            services["redis"] = "disabled"
    except Exception as e:
        services["redis"] = f"error: {str(e)[:50]}"
        degraded_services.append("redis")

    # ===== Celery Job Queue =====
    try:
        if settings.redis_enabled:
            from junior.workers import app as celery_app
            # Try to reach the broker
            celery_app.control.inspect().active()
            services["celery"] = "ready"
        else:
            services["celery"] = "disabled"
    except Exception as e:
        services["celery"] = f"error: {str(e)[:50]}"
        logger.debug(f"Celery health check failed: {e}")

    # ===== Core Services =====
    # Check PII redaction
    if settings.enable_pii_redaction:
        services["pii_redaction"] = "enabled"
    else:
        services["pii_redaction"] = "disabled"

    # Check embeddings
    if settings.embedding_model:
        services["embeddings"] = f"configured ({settings.embedding_model[:20]}...)"
    else:
        services["embeddings"] = "not_configured"

    # Determine overall status
    # Degraded if optional services are down, unhealthy if critical services fail
    critical_services = ["groq", "supabase"]
    critical_degraded = [s for s in degraded_services if s in critical_services]

    if critical_degraded:
        overall_status = "unhealthy"
    elif degraded_services:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        environment=settings.app_env,
        services=services,
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get("/health/redis")
async def redis_health():
    """Check Redis status specifically."""
    try:
        if not settings.redis_enabled:
            return {"status": "disabled", "message": "Redis is disabled"}

        from junior.db import get_redis_client
        redis_client = await get_redis_client()
        health = await redis_client.health_check()

        if health:
            return {
                "status": "healthy",
                "service": "redis",
                "url": settings.redis_url[:30] + "***",  # Hide password
                "db": settings.redis_db,
            }
        else:
            return {"status": "unhealthy", "service": "redis", "message": "Connection failed"}

    except Exception as e:
        logger.error(f"Redis health check error: {e}")
        return {"status": "error", "service": "redis", "message": str(e)}


@router.get("/health/wall")
async def wall_health():
    """Check Detective Wall service status."""
    try:
        from junior.services.wall_service import get_wall_service

        service = await get_wall_service()

        return {
            "status": "healthy",
            "service": "detective_wall",
            "message": "Wall service initialized",
            "features": [
                "cached_analysis",
                "snapshots",
                "proactive_suggestions",
                "async_analysis",
                "enhanced_provenance",
            ],
        }

    except Exception as e:
        logger.error(f"Wall service health check error: {e}")
        return {"status": "error", "service": "detective_wall", "message": str(e)}


@router.get("/")
async def root():
    """Root endpoint - returns API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Junior - Your Trusted AI Legal Assistant",
        "docs": "/docs",
        "health": "/api/v1/health",
        "health_redis": "/api/v1/health/redis",
        "health_wall": "/api/v1/health/wall",
        "status": "online",
    }
