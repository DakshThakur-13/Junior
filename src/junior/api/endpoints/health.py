"""
Health check endpoints
"""

from fastapi import APIRouter

from junior.core import settings
from junior.api.schemas import HealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint

    Returns service status and version information
    """
    services = {}

    # Check Groq API
    if settings.groq_api_key:
        services["groq"] = "configured"
    else:
        services["groq"] = "not_configured"

    # Check Supabase
    if settings.supabase_url and settings.supabase_key:
        services["supabase"] = "configured"
    else:
        services["supabase"] = "not_configured"

    # Check PII redaction
    if settings.enable_pii_redaction:
        services["pii_redaction"] = "enabled"
    else:
        services["pii_redaction"] = "disabled"

    return HealthResponse(
        status="healthy",
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
