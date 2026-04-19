"""Admin endpoints for system management"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from junior.core import get_logger, settings
from . import auth
from junior.services.audit_log import recent_audit_events, verify_audit_chain
from junior.services.security_incident import get_incident_service

router = APIRouter()
logger = get_logger(__name__)


class Phase1DetectRequest(BaseModel):
    title: str = Field(min_length=4, max_length=200)
    summary: str = Field(min_length=8, max_length=1000)
    source_ip: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)


class Phase2ContainRequest(BaseModel):
    incident_id: str
    systems: list[str] = Field(default_factory=list)
    ips: list[str] = Field(default_factory=list)
    credential_ids: list[str] = Field(default_factory=list)
    evidence_note: Optional[str] = None
    evidence_artifacts: list[str] = Field(default_factory=list)


@router.post("/clear-cache")
async def clear_search_cache(_: str = Depends(auth.require_ops_admin)):
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


@router.get("/clear-cache")
async def clear_search_cache_get(_: str = Depends(auth.require_ops_admin)):
    """GET alias for cache clear (keeps manual checks compatible)."""
    return await clear_search_cache()


@router.get("/health-detailed")
async def detailed_health(_: str = Depends(auth.require_ops_admin)):
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
async def system_info(_: str = Depends(auth.require_ops_admin)):
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


@router.get("/audit/events")
async def get_audit_events(
    limit: int = 100,
    case_id: Optional[str] = None,
    _: str = Depends(auth.require_security_admin),
):
    """Return recent append-only audit events."""
    return {
        "events": recent_audit_events(limit=limit, case_id=case_id),
        "limit": max(1, min(limit, 1000)),
        "case_id": case_id,
    }


@router.get("/audit/verify")
async def verify_audit(_: str = Depends(auth.require_security_admin)):
    """Verify tamper-evident hash chain integrity for audit events."""
    return verify_audit_chain()


@router.get("/security/status")
async def security_status(_: str = Depends(auth.require_security_admin)):
    """View Phase 1 and Phase 2 security response state."""
    return get_incident_service().get_status()


@router.post("/security/phase1/detect")
async def security_phase1_detect(payload: Phase1DetectRequest, _: str = Depends(auth.require_security_admin)):
    """Phase 1: Detection (alerts, notification, initial assessment)."""
    incident = get_incident_service().start_phase1_detection(
        title=payload.title,
        summary=payload.summary,
        source_ip=payload.source_ip,
        details=payload.details,
    )
    return {
        "status": "phase1_completed",
        "incident": incident,
        "actions": [
            "automated_alert_triggered",
            "security_team_notified",
            "initial_assessment_started",
        ],
    }


@router.post("/security/phase2/contain")
async def security_phase2_contain(payload: Phase2ContainRequest, _: str = Depends(auth.require_security_admin)):
    """Phase 2: Containment (isolate systems, block IPs, revoke credentials, preserve evidence)."""
    try:
        incident = get_incident_service().run_phase2_containment(
            incident_id=payload.incident_id,
            systems=payload.systems,
            ips=payload.ips,
            credential_ids=payload.credential_ids,
            evidence_note=payload.evidence_note,
            evidence_artifacts=payload.evidence_artifacts,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "status": "phase2_completed",
        "incident": incident,
        "actions": [
            "affected_systems_isolated",
            "malicious_ips_blocked",
            "credentials_revoked",
            "evidence_preserved",
        ],
    }
