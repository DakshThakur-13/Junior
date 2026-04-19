"""
API Router - Main router combining all endpoint groups
"""

from fastapi import APIRouter
from fastapi import FastAPI
from fastapi import Depends

from .endpoints import research, documents, chat, chat_stream, translate, format, health, judges, cases, websocket, audio, admin, consent, workbench, auth
from .endpoints.wall import router as wall_router

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_router.include_router(
    health.router,
    tags=["Health"],
)

api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["Admin"],
)

api_router.include_router(
    auth.router,
    tags=["Authentication"],
)

api_router.include_router(
    consent.router,
    tags=["Consent & Privacy"],
)

api_router.include_router(
    audio.router,
    prefix="/audio",
    tags=["Audio"],
    dependencies=[Depends(auth.require_auth)],
)

api_router.include_router(
    research.router,
    prefix="/research",
    tags=["Research"],
    dependencies=[Depends(auth.require_auth)],
)

api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["Documents"],
    dependencies=[Depends(auth.require_auth)],
)

api_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["Chat"],
    dependencies=[Depends(auth.require_auth)],
)

# Note: chat_stream uses same /chat prefix but different routes (/stream)
api_router.include_router(
    chat_stream.router,
    prefix="/chat",
    tags=["Chat Streaming"],
    dependencies=[Depends(auth.require_auth)],
)

api_router.include_router(
    translate.router,
    prefix="/translate",
    tags=["Translation"],
)

api_router.include_router(
    format.router,
    prefix="/format",
    tags=["Formatting"],
)

api_router.include_router(
    judges.router,
    prefix="/judges",
    tags=["Judges"],
)

api_router.include_router(
    cases.router,
    prefix="/cases",
    tags=["Cases"],
    dependencies=[Depends(auth.require_auth)],
)

api_router.include_router(
    workbench.router,
    prefix="/workbench",
    tags=["Workbench"],
    dependencies=[Depends(auth.require_auth)],
)

api_router.include_router(
    wall_router,
    prefix="/wall",
    tags=["DetectiveWall"],
    dependencies=[Depends(auth.require_auth)],
)

# WebSocket routes (no prefix, handled at root)
api_router.include_router(
    websocket.router,
    tags=["WebSocket"],
)


def create_app() -> FastAPI:
    """Create a minimal FastAPI app with the v1 API router attached."""
    app = FastAPI(title="Junior API")
    app.include_router(api_router)
    return app
