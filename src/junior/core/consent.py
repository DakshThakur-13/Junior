"""
User Consent Management System
Handles collection, storage, and validation of user consents for GDPR/DPDP compliance
"""
import logging
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ConsentType(str, Enum):
    """Types of consent that can be requested from users"""
    ESSENTIAL_SERVICES = "essential_services"  # Required for service operation
    DATA_PROCESSING = "data_processing"  # Process legal documents and case data
    ANALYTICS = "analytics"  # Usage analytics and improvement
    THIRD_PARTY_AI = "third_party_ai"  # Share data with AI providers (Groq, etc.)
    AUDIO_TRANSCRIPTION = "audio_transcription"  # Record and transcribe audio
    EMAIL_NOTIFICATIONS = "email_notifications"  # Non-essential emails
    COOKIES_ANALYTICS = "cookies_analytics"  # Non-essential cookies


class ConsentStatus(str, Enum):
    """Status of a consent"""
    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class ConsentRecord(BaseModel):
    """Individual consent record"""
    consent_id: str = Field(..., description="Unique consent identifier")
    user_id: str = Field(..., description="User identifier")
    consent_type: ConsentType = Field(..., description="Type of consent")
    status: ConsentStatus = Field(..., description="Current status")
    granted_at: Optional[datetime] = Field(None, description="When consent was granted")
    withdrawn_at: Optional[datetime] = Field(None, description="When consent was withdrawn")
    expires_at: Optional[datetime] = Field(None, description="Consent expiration date")
    ip_address: Optional[str] = Field(None, description="IP address when consent given")
    user_agent: Optional[str] = Field(None, description="Browser/device info")
    version: str = Field("1.0", description="Privacy policy version")
    purpose: str = Field(..., description="Human-readable purpose")
    legal_basis: str = Field(..., description="GDPR legal basis (consent, contract, etc.)")


class ConsentRequest(BaseModel):
    """Request for user consent"""
    consent_type: ConsentType
    required: bool = Field(..., description="Whether consent is mandatory")
    title: str = Field(..., description="Short title")
    description: str = Field(..., description="Detailed explanation")
    legal_basis: str = Field(..., description="GDPR Article 6 basis")
    retention_period: str = Field(..., description="How long data is kept")
    
    class Config:
        json_schema_extra = {
            "example": {
                "consent_type": "data_processing",
                "required": True,
                "title": "Legal Document Processing",
                "description": "We need your consent to process and analyze your legal documents using AI.",
                "legal_basis": "Consent (GDPR Art. 6(1)(a))",
                "retention_period": "7 years as per Indian Evidence Act"
            }
        }


class ConsentBundle(BaseModel):
    """Bundle of consent requests shown to user"""
    policy_version: str = Field("1.0", description="Privacy policy version")
    policy_url: str = Field("/privacy-policy", description="Link to full policy")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    consents: List[ConsentRequest] = Field(..., description="List of consent requests")


class UserConsentProfile(BaseModel):
    """User's complete consent profile"""
    user_id: str
    consents: Dict[ConsentType, ConsentRecord] = Field(default_factory=dict)
    profile_complete: bool = Field(False, description="All required consents obtained")
    last_review_date: Optional[datetime] = None
    next_review_date: Optional[datetime] = None


# Default consent bundle for new users
DEFAULT_CONSENT_BUNDLE = ConsentBundle(
    policy_version="1.0",
    policy_url="/docs/PRIVACY_POLICY.md",
    consents=[
        ConsentRequest(
            consent_type=ConsentType.ESSENTIAL_SERVICES,
            required=True,
            title="Essential Services",
            description="Authentication, session management, and core functionality. Required to use Junior.",
            legal_basis="Performance of Contract (GDPR Art. 6(1)(b))",
            retention_period="Account lifetime + 30 days"
        ),
        ConsentRequest(
            consent_type=ConsentType.DATA_PROCESSING,
            required=True,
            title="Legal Document Processing",
            description="Analyze and process your legal documents, case files, and evidence using AI technology.",
            legal_basis="Consent (GDPR Art. 6(1)(a))",
            retention_period="7 years (Indian Evidence Act) or until you delete"
        ),
        ConsentRequest(
            consent_type=ConsentType.THIRD_PARTY_AI,
            required=True,
            title="AI Service Providers",
            description="Share anonymized queries with Groq, Perplexity, and HuggingFace for AI processing. No personal identifiers are sent.",
            legal_basis="Consent (GDPR Art. 6(1)(a))",
            retention_period="Processed in real-time, not stored by providers"
        ),
        ConsentRequest(
            consent_type=ConsentType.AUDIO_TRANSCRIPTION,
            required=False,
            title="Audio Recording & Transcription",
            description="Record and transcribe audio for legal documentation. Audio is deleted after transcription.",
            legal_basis="Consent (GDPR Art. 6(1)(a))",
            retention_period="Raw audio: Immediate deletion. Transcripts: 90 days"
        ),
        ConsentRequest(
            consent_type=ConsentType.ANALYTICS,
            required=False,
            title="Usage Analytics",
            description="Collect anonymized usage statistics to improve Junior's features and performance.",
            legal_basis="Legitimate Interest (GDPR Art. 6(1)(f))",
            retention_period="2 years (anonymized)"
        ),
        ConsentRequest(
            consent_type=ConsentType.COOKIES_ANALYTICS,
            required=False,
            title="Analytics Cookies",
            description="Use cookies to track feature usage and improve user experience. Essential cookies cannot be disabled.",
            legal_basis="Consent (GDPR Art. 6(1)(a)) / ePrivacy Directive",
            retention_period="Session duration or until you clear cookies"
        ),
        ConsentRequest(
            consent_type=ConsentType.EMAIL_NOTIFICATIONS,
            required=False,
            title="Email Notifications",
            description="Send non-essential emails about new features, tips, and updates. Security alerts are always sent.",
            legal_basis="Consent (GDPR Art. 6(1)(a))",
            retention_period="Until you unsubscribe"
        ),
    ]
)


class ConsentManager:
    """
    Service for managing user consents
    
    Usage:
        manager = ConsentManager(user_id="user123")
        await manager.request_consent(ConsentType.DATA_PROCESSING)
        if await manager.has_consent(ConsentType.DATA_PROCESSING):
            # Process data
            pass
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.profile = UserConsentProfile(user_id=user_id)
    
    async def get_consent_bundle(self) -> ConsentBundle:
        """Get consent bundle for user to review"""
        return DEFAULT_CONSENT_BUNDLE
    
    async def grant_consent(
        self,
        consent_type: ConsentType,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ConsentRecord:
        """Grant a specific consent"""
        record = ConsentRecord(
            consent_id=f"{self.user_id}_{consent_type.value}_{datetime.utcnow().timestamp()}",
            user_id=self.user_id,
            consent_type=consent_type,
            status=ConsentStatus.GRANTED,
            granted_at=datetime.utcnow(),
            ip_address=ip_address,
            user_agent=user_agent,
            version="1.0",
            purpose=self._get_purpose(consent_type),
            legal_basis=self._get_legal_basis(consent_type)
        )
        
        self.profile.consents[consent_type] = record
        await self._save_consent(record)
        return record
    
    async def withdraw_consent(self, consent_type: ConsentType) -> None:
        """Withdraw a previously granted consent"""
        if consent_type in self.profile.consents:
            record = self.profile.consents[consent_type]
            record.status = ConsentStatus.WITHDRAWN
            record.withdrawn_at = datetime.utcnow()
            await self._save_consent(record)
    
    async def has_consent(self, consent_type: ConsentType) -> bool:
        """Check if user has granted a specific consent"""
        if consent_type not in self.profile.consents:
            return False
        
        record = self.profile.consents[consent_type]
        return record.status == ConsentStatus.GRANTED
    
    async def check_required_consents(self) -> bool:
        """Verify all required consents are granted"""
        required = [
            ConsentType.ESSENTIAL_SERVICES,
            ConsentType.DATA_PROCESSING,
            ConsentType.THIRD_PARTY_AI
        ]
        
        for consent_type in required:
            if not await self.has_consent(consent_type):
                return False
        return True
    
    async def get_consent_summary(self) -> Dict[str, any]:
        """Get summary of user's consent status"""
        return {
            "user_id": self.user_id,
            "profile_complete": await self.check_required_consents(),
            "consents": {
                ct.value: {
                    "granted": await self.has_consent(ct),
                    "granted_at": self.profile.consents[ct].granted_at.isoformat() if ct in self.profile.consents else None
                }
                for ct in ConsentType
            },
            "last_review": self.profile.last_review_date,
            "next_review": self.profile.next_review_date
        }
    
    def _get_purpose(self, consent_type: ConsentType) -> str:
        """Get human-readable purpose for consent type"""
        purposes = {
            ConsentType.ESSENTIAL_SERVICES: "Provide core application functionality",
            ConsentType.DATA_PROCESSING: "Process legal documents and case data",
            ConsentType.ANALYTICS: "Improve service through usage analytics",
            ConsentType.THIRD_PARTY_AI: "Enable AI features via external providers",
            ConsentType.AUDIO_TRANSCRIPTION: "Transcribe audio recordings",
            ConsentType.EMAIL_NOTIFICATIONS: "Send non-essential emails",
            ConsentType.COOKIES_ANALYTICS: "Track usage with analytics cookies"
        }
        return purposes.get(consent_type, "General data processing")
    
    def _get_legal_basis(self, consent_type: ConsentType) -> str:
        """Get GDPR legal basis for consent type"""
        bases = {
            ConsentType.ESSENTIAL_SERVICES: "Contract (GDPR Art. 6(1)(b))",
            ConsentType.DATA_PROCESSING: "Consent (GDPR Art. 6(1)(a))",
            ConsentType.ANALYTICS: "Legitimate Interest (GDPR Art. 6(1)(f))",
            ConsentType.THIRD_PARTY_AI: "Consent (GDPR Art. 6(1)(a))",
            ConsentType.AUDIO_TRANSCRIPTION: "Consent (GDPR Art. 6(1)(a))",
            ConsentType.EMAIL_NOTIFICATIONS: "Consent (GDPR Art. 6(1)(a))",
            ConsentType.COOKIES_ANALYTICS: "Consent (GDPR Art. 6(1)(a))"
        }
        return bases.get(consent_type, "Consent (GDPR Art. 6(1)(a))")
    
    async def _save_consent(self, record: ConsentRecord) -> None:
        """Save consent record to database with fallback to local storage"""
        try:
            from junior.db import get_supabase_client
            client = get_supabase_client()
            
            # Upsert to Supabase user_consents table
            consent_data = {
                "user_id": self.user_id,
                "consent_type": record.consent_type.value,
                "status": record.status.value,
                "granted_at": record.granted_at.isoformat() if record.granted_at else None,
                "withdrawn_at": record.withdrawn_at.isoformat() if record.withdrawn_at else None,
                "ip_address": record.ip_address,
                "user_agent": record.user_agent,
                "legal_basis": record.legal_basis,
                "version": record.version,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = await client.table("user_consents").upsert(
                consent_data,
                on_conflict="user_id,consent_type"
            ).execute()
            
            logger.info(f"Consent saved to Supabase for user {self.user_id}: {record.consent_type.value}")
            
        except Exception as e:
            logger.warning(f"Failed to save consent to Supabase: {e}. Using local fallback.")
            
            # Fallback: save to local JSON file
            try:
                from pathlib import Path
                consent_dir = Path("uploads") / "consents"
                consent_dir.mkdir(parents=True, exist_ok=True)
                
                consent_file = consent_dir / f"{self.user_id}_consents.json"
                
                # Load existing consents or create new
                consents = {}
                if consent_file.exists():
                    import json
                    with open(consent_file, 'r') as f:
                        consents = json.load(f)
                
                # Update with new record
                consents[record.consent_type.value] = {
                    "status": record.status.value,
                    "granted_at": record.granted_at.isoformat() if record.granted_at else None,
                    "withdrawn_at": record.withdrawn_at.isoformat() if record.withdrawn_at else None,
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                import json
                with open(consent_file, 'w') as f:
                    json.dump(consents, f, indent=2)
                
                logger.info(f"Consent saved to local storage for user {self.user_id}: {record.consent_type.value}")
                
            except Exception as e2:
                logger.error(f"Failed to save consent even to local storage: {e2}")
