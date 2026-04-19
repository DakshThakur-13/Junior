"""
Consent Management API Endpoints
Provides endpoints for users to manage their data processing consents
"""
from fastapi import APIRouter, HTTPException, Header, Request
from typing import Dict, List, Any
from datetime import datetime, timedelta
from junior.core import get_logger

logger = get_logger(__name__)
from junior.core.consent import (
    ConsentManager,
    ConsentType,
    ConsentBundle,
    ConsentRecord,
    DEFAULT_CONSENT_BUNDLE
)
from junior.api.endpoints.auth import resolve_user_id

# Note: Global /api/v1 prefix applied in main.py
router = APIRouter(prefix="/consent", tags=["consent"])


@router.get("/bundle", response_model=ConsentBundle)
async def get_consent_bundle():
    """
    Get the consent bundle for user review
    
    Shows all available consents with descriptions, legal basis, and retention periods.
    Used during onboarding and consent review.
    """
    return DEFAULT_CONSENT_BUNDLE


@router.post("/grant/{consent_type}")
async def grant_consent(
    consent_type: ConsentType,
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
) -> ConsentRecord:
    """
    Grant a specific consent
    
    Records user consent with IP address and timestamp for audit trail.
    """
    user_id = resolve_user_id(authorization, x_user_id)
    manager = ConsentManager(user_id=user_id)
    
    # Extract request metadata
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    try:
        record = await manager.grant_consent(
            consent_type=consent_type,
            ip_address=ip_address,
            user_agent=user_agent
        )
        return record
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to grant consent: {str(e)}")


@router.post("/withdraw/{consent_type}")
async def withdraw_consent(
    consent_type: ConsentType,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    """
    Withdraw a previously granted consent
    
    GDPR Article 7(3): Right to withdraw consent at any time.
    Withdrawing required consents will terminate service access.
    """
    user_id = resolve_user_id(authorization, x_user_id)
    manager = ConsentManager(user_id=user_id)
    
    try:
        await manager.withdraw_consent(consent_type)
        return {
            "status": "success",
            "message": f"Consent {consent_type.value} withdrawn",
            "warning": "Service functionality may be limited" if consent_type in [
                ConsentType.ESSENTIAL_SERVICES,
                ConsentType.DATA_PROCESSING
            ] else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to withdraw consent: {str(e)}")


@router.get("/status")
async def get_consent_status(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
) -> Dict:
    """
    Get user's current consent status
    
    Returns which consents are granted, denied, or withdrawn.
    """
    user_id = resolve_user_id(authorization, x_user_id)
    manager = ConsentManager(user_id=user_id)
    
    try:
        summary = await manager.get_consent_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get consent status: {str(e)}")


@router.get("/check-required")
async def check_required_consents(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
) -> Dict[str, bool]:
    """
    Check if all required consents are granted
    
    Used to verify user can access the service.
    """
    user_id = resolve_user_id(authorization, x_user_id)
    manager = ConsentManager(user_id=user_id)
    
    try:
        complete = await manager.check_required_consents()
        return {
            "profile_complete": complete,
            "can_use_service": complete,
            "missing_consents": [] if complete else [
                ct.value for ct in [
                    ConsentType.ESSENTIAL_SERVICES,
                    ConsentType.DATA_PROCESSING,
                    ConsentType.THIRD_PARTY_AI
                ] if not await manager.has_consent(ct)
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check consents: {str(e)}")


@router.post("/grant-bundle")
async def grant_consent_bundle(
    consent_types: List[ConsentType],
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
) -> Dict[str, Any]:
    """
    Grant multiple consents at once
    
    Used during onboarding to accept multiple consents together.
    """
    user_id = resolve_user_id(authorization, x_user_id)
    manager = ConsentManager(user_id=user_id)
    
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    results = []
    for consent_type in consent_types:
        try:
            record = await manager.grant_consent(
                consent_type=consent_type,
                ip_address=ip_address,
                user_agent=user_agent
            )
            results.append({
                "consent_type": consent_type.value,
                "status": "granted",
                "record_id": record.consent_id
            })
        except Exception as e:
            results.append({
                "consent_type": consent_type.value,
                "status": "error",
                "error": str(e)
            })
    
    complete = await manager.check_required_consents()
    
    return {
        "results": results,
        "profile_complete": complete,
        "granted_count": len([r for r in results if r["status"] == "granted"]),
        "error_count": len([r for r in results if r["status"] == "error"])
    }


@router.delete("/revoke-all")
async def revoke_all_consents(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
) -> Dict:
    """
    Revoke all consents and request account deletion
    
    GDPR Article 17: Right to erasure ("right to be forgotten").
    This initiates the account deletion process.
    """
    from junior.services.audit_log import audit_log
    from datetime import datetime
    
    user_id = resolve_user_id(authorization, x_user_id)
    manager = ConsentManager(user_id=user_id)
    
    try:
        # Withdraw all consents
        for consent_type in ConsentType:
            if await manager.has_consent(consent_type):
                await manager.withdraw_consent(consent_type)
        
        # Trigger account deletion workflow
        from junior.db import get_supabase_client
        try:
            client = get_supabase_client()
            
            # Mark user for deletion in Supabase
            deletion_data = {
                "user_id": user_id,
                "deletion_requested_at": datetime.utcnow().isoformat(),
                "deletion_scheduled_for": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                "status": "pending_deletion"
            }
            
            await client.table("user_deletions").upsert(
                deletion_data,
                on_conflict="user_id"
            ).execute()
            
            # Audit the deletion request
            await audit_log(
                event_type="account_deletion_requested",
                actor=user_id,
                target=f"user:{user_id}",
                details={"reason": "user_revoked_all_consents", "timestamp": datetime.utcnow().isoformat()}
            )
            
        except Exception as e:
            logger.warning(f"Failed to schedule deletion in Supabase: {e}")
            # Continue even if database fails - at least consents are withdrawn
        
        return {
            "status": "success",
            "message": "All consents revoked. Account deletion initiated.",
            "deletion_timeline": "Your data will be deleted within 30 days.",
            "contact": "privacy@junior-legal.com for questions"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to revoke consents: {str(e)}")


@router.get("/export")
async def export_consent_records(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
) -> Dict:
    """
    Export user's consent records
    
    GDPR Article 20: Right to data portability.
    Returns all consent records in machine-readable format.
    """
    user_id = resolve_user_id(authorization, x_user_id)
    manager = ConsentManager(user_id=user_id)
    
    from datetime import datetime
    try:
        return {
            "user_id": user_id,
            "export_date": datetime.utcnow().isoformat() + "Z",
            "policy_version": "1.0",
            "consents": manager.profile.consents,
            "format": "application/json",
            "note": "This is your complete consent history per GDPR Article 20"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export consents: {str(e)}")
