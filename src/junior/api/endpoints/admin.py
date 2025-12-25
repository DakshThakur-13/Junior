"""Admin endpoints for system management"""
from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional

from junior.core import get_logger, settings

router = APIRouter()
logger = get_logger(__name__)


def verify_admin_key(x_admin_key: Optional[str] = Header(None)):
    """Simple admin key verification"""
    # In development, allow if debug mode is on
    if settings.app_debug and settings.is_development:
        return True
    
    admin_key = getattr(settings, 'admin_api_key', None)
    if not admin_key:
        raise HTTPException(
            status_code=403, 
            detail="Admin API key not configured. Set ADMIN_API_KEY in .env"
        )
    
    if not x_admin_key or x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    return True


@router.post("/clear-cache")
async def clear_search_cache(_: bool = Depends(verify_admin_key)):
    """Clear the search results cache"""
    try:
        from junior.services.official_sources import SEARCH_CACHE
        cache_size = len(SEARCH_CACHE)
        SEARCH_CACHE.clear()
        logger.info(f"Search cache cleared ({cache_size} entries)")
        return {
            "status": "success", 
            "message": f"Search cache cleared ({cache_size} entries)"
        }
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health-detailed")
async def detailed_health(_: bool = Depends(verify_admin_key)):
    """Detailed health check with service status"""
    status = {
        "api": "healthy",
        "services": {},
        "config": {},
    }
    
    # Check services
    try:
        from junior.services.translator import TranslationService
        TranslationService()
        status["services"]["translation"] = "ok"
    except Exception as e:
        status["services"]["translation"] = f"error: {str(e)}"
    
    try:
        from junior.services.conversational_chat import ConversationalChat
        ConversationalChat()
        status["services"]["chat"] = "ok"
    except Exception as e:
        status["services"]["chat"] = f"error: {str(e)}"
    
    try:
        from junior.services.official_sources import OfficialSourcesService
        OfficialSourcesService()
        status["services"]["sources"] = "ok"
    except Exception as e:
        status["services"]["sources"] = f"error: {str(e)}"
    
    try:
        from junior.services.legal_glossary import get_glossary_service
        get_glossary_service()
        status["services"]["glossary"] = "ok"
    except Exception as e:
        status["services"]["glossary"] = f"error: {str(e)}"
    
    try:
        from junior.services.transcriber import TranscriberService
        TranscriberService()
        status["services"]["transcriber"] = "ok"
    except Exception as e:
        status["services"]["transcriber"] = f"error: {str(e)}"
    
    # Check config
    status["config"]["groq"] = bool(settings.groq_api_key)
    status["config"]["perplexity"] = bool(settings.perplexity_api_key)
    status["config"]["huggingface"] = bool(settings.huggingface_api_key)
    status["config"]["supabase"] = bool(settings.supabase_url)
    status["config"]["pii_redaction"] = settings.enable_pii_redaction
    
    return status


@router.get("/info")
async def system_info(_: bool = Depends(verify_admin_key)):
    """System information"""
    import sys
    import platform
    
    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "environment": settings.app_env,
        "debug_mode": settings.app_debug,
        "python_version": sys.version,
        "platform": platform.platform(),
        "host": settings.host,
        "port": settings.port,
    }
