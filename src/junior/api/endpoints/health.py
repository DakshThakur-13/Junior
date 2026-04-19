"""
Health check endpoints
"""

from fastapi import APIRouter

from junior.core import settings
from junior.api.schemas import HealthResponse
from junior.db import get_supabase_client

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint

    Returns service status and version information
    """
    services = {}
    degraded_services = []

    # Check Groq API
    if settings.groq_api_key:
        services["groq"] = "configured"
    else:
        services["groq"] = "not_configured"
        degraded_services.append("groq")

    # Check Supabase
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

    # Check PII redaction
    if settings.enable_pii_redaction:
        services["pii_redaction"] = "enabled"
    else:
        services["pii_redaction"] = "disabled"

    # Determine overall status based on critical service health
    overall_status = "healthy" if not degraded_services else "degraded"

    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        environment=settings.app_env,
        services=services,
    )

@router.get("/")
async def root():
    """Root endpoint - returns API information"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Junior - Your Trusted AI Legal Assistant",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
