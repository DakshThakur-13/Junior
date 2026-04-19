"""Authentication endpoints for signup/signin/token verification."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

import jwt
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from junior.core import get_logger, settings
from junior.db import get_supabase_client
from junior.services.security_incident import get_incident_service

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

SECRET_KEY = settings.app_secret_key
ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24
ADMIN_ROLES = {"admin", "ops_admin", "security_admin"}


class SignUpRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str = Field(min_length=2, max_length=120)
    bar_council_id: Optional[str] = None


class SignInRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


def _create_access_token(user_id: str, email: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta is None:
        expires_delta = timedelta(hours=TOKEN_EXPIRY_HOURS)

    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "email": email,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expired") from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    user_id = payload.get("user_id")
    email = payload.get("email")
    if not user_id or not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    return {"user_id": user_id, "email": email}


def _extract_bearer_token(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    return authorization[7:]


def resolve_user_id(authorization: Optional[str], x_user_id: Optional[str]) -> str:
    """Resolve current user id from bearer token, with legacy header fallback."""
    if authorization and authorization.startswith("Bearer "):
        token = _extract_bearer_token(authorization)
        claims = _decode_token(token)
        return str(claims["user_id"])

    if x_user_id:
        return str(x_user_id)

    raise HTTPException(status_code=401, detail="Authentication required")


async def require_auth(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-ID"),
) -> str:
    """FastAPI dependency to enforce authenticated access on protected routes."""
    return resolve_user_id(authorization, x_user_id)


def _get_user_role(user_id: str) -> str:
    sb = get_supabase_client().client
    user_row = sb.table("users").select("id, role").eq("id", user_id).limit(1).execute()
    if not user_row.data:
        raise HTTPException(status_code=403, detail="Admin access required")
    return str(user_row.data[0].get("role", "")).lower()


def _enforce_roles(authorization: Optional[str], allowed_roles: Sequence[str]) -> str:
    token = _extract_bearer_token(authorization)
    claims = _decode_token(token)
    role = _get_user_role(str(claims["user_id"]))
    if role not in {r.lower() for r in allowed_roles}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return str(claims["user_id"])


async def require_admin(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> str:
    """FastAPI dependency for any admin-class role."""
    return _enforce_roles(authorization, tuple(ADMIN_ROLES))


async def require_ops_admin(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> str:
    """Allow operational admin actions."""
    return _enforce_roles(authorization, ("admin", "ops_admin"))


async def require_security_admin(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> str:
    """Allow security and audit-sensitive admin actions."""
    return _enforce_roles(authorization, ("admin", "security_admin"))


@router.post("/signup", response_model=TokenResponse)
async def signup(request: SignUpRequest) -> TokenResponse:
    sb = get_supabase_client().client

    existing = sb.table("users").select("id").eq("email", request.email).limit(1).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="Email already registered")

    try:
        auth_response = sb.auth.sign_up({"email": request.email, "password": request.password})
    except Exception as exc:
        error_text = str(exc).lower()
        status_code = int(getattr(exc, "status", 0) or getattr(exc, "status_code", 0) or 0)
        if status_code == 429 or "rate limit" in error_text:
            raise HTTPException(
                status_code=429,
                detail="Signup is temporarily rate-limited. Please try again shortly.",
            ) from exc
        if "already" in error_text and ("registered" in error_text or "exists" in error_text):
            raise HTTPException(status_code=409, detail="Email already registered") from exc
        logger.exception("Signup provider error for %s", request.email)
        raise HTTPException(
            status_code=502,
            detail="Authentication provider unavailable. Please try again later.",
        ) from exc

    if not auth_response.user:
        raise HTTPException(status_code=500, detail="Failed to create user")

    user_id = auth_response.user.id
    now = datetime.now(timezone.utc).isoformat()
    user_data = {
        "id": user_id,
        "email": request.email,
        "name": request.name,
        "bar_council_id": request.bar_council_id,
        "role": "lawyer",
        "preferred_language": "ENGLISH",
        "subscription_tier": "free",
        "settings": {},
        "usage_stats": {},
        "created_at": now,
        "updated_at": now,
    }
    try:
        sb.table("users").insert(user_data).execute()
    except Exception as exc:
        logger.exception("Failed creating user profile row for %s", request.email)
        raise HTTPException(status_code=500, detail="User created but profile setup failed") from exc

    token = _create_access_token(user_id, request.email)
    logger.info(f"User signed up: {request.email} ({user_id})")

    return TokenResponse(
        access_token=token,
        user={"id": user_id, "email": request.email, "name": request.name, "role": "lawyer"},
    )


@router.post("/signin", response_model=TokenResponse)
async def signin(request: SignInRequest, http_request: Request) -> TokenResponse:
    sb = get_supabase_client().client
    client_ip = http_request.client.host if http_request.client else None
    incident_service = get_incident_service()

    try:
        auth_response = sb.auth.sign_in_with_password({"email": request.email, "password": request.password})
    except Exception as exc:
        incident = incident_service.record_failed_login(request.email, client_ip)
        if incident:
            logger.warning(
                "Phase 1 incident auto-triggered from signin failures: %s",
                incident.get("id"),
            )
        raise HTTPException(status_code=401, detail="Invalid email or password") from exc

    if not auth_response.user:
        incident = incident_service.record_failed_login(request.email, client_ip)
        if incident:
            logger.warning(
                "Phase 1 incident auto-triggered from signin failures: %s",
                incident.get("id"),
            )
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_id = auth_response.user.id
    user_row = sb.table("users").select("*").eq("id", user_id).limit(1).execute()
    if not user_row.data:
        raise HTTPException(status_code=404, detail="User profile not found")

    sb.table("users").update({"last_login_at": datetime.utcnow().isoformat()}).eq("id", user_id).execute()

    user = user_row.data[0]
    token = _create_access_token(user_id, request.email)
    incident_service.clear_failed_login_window(request.email, client_ip)
    logger.info(f"User signed in: {request.email} ({user_id})")

    return TokenResponse(
        access_token=token,
        user={
            "id": user.get("id"),
            "email": user.get("email"),
            "name": user.get("name"),
            "role": user.get("role"),
            "bar_council_id": user.get("bar_council_id"),
        },
    )


@router.get("/me")
async def me(authorization: Optional[str] = Header(default=None, alias="Authorization")) -> dict:
    token = _extract_bearer_token(authorization)
    claims = _decode_token(token)

    sb = get_supabase_client().client
    user_row = sb.table("users").select("*").eq("id", claims["user_id"]).limit(1).execute()
    if not user_row.data:
        raise HTTPException(status_code=404, detail="User not found")

    return user_row.data[0]


@router.post("/refresh")
async def refresh(authorization: Optional[str] = Header(default=None, alias="Authorization")) -> dict:
    token = _extract_bearer_token(authorization)
    claims = _decode_token(token)
    return {
        "access_token": _create_access_token(claims["user_id"], claims["email"]),
        "token_type": "bearer",
    }


@router.post("/verify")
async def verify(authorization: Optional[str] = Header(default=None, alias="Authorization")) -> dict:
    token = _extract_bearer_token(authorization)
    claims = _decode_token(token)
    return {"valid": True, **claims}
