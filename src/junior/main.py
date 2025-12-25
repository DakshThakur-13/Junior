"""Junior - Your Trusted AI Legal Assistant.

Main FastAPI Application Entry Point.

Serves the professional Vite/React frontend build from `frontend/dist`.
"""

from pathlib import Path
from contextlib import asynccontextmanager
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from junior.core import settings, get_logger
from junior.api import api_router

logger = get_logger(__name__)

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
FRONTEND_DIST_DIR = PROJECT_ROOT / "frontend" / "dist"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager

    Handles startup and shutdown events
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.app_env}")

    # Verify configurations
    if not settings.groq_api_key:
        logger.warning("⚠️  GROQ_API_KEY not configured - LLM features will not work")
    else:
        logger.info("✅ Groq API configured")

    if not settings.supabase_url:
        logger.warning("⚠️  Supabase not configured - database features will not work")
    else:
        logger.info("✅ Supabase configured")

    if settings.enable_pii_redaction:
        logger.info("✅ PII Redaction enabled")

    # Pre-initialize glossary service
    try:
        from junior.services.legal_glossary import get_glossary_service
        glossary = get_glossary_service()
        # Glossary is initialized lazily, just ensure it's imported
        logger.info("✅ Legal glossary service ready")
    except Exception as e:
        logger.warning(f"⚠️  Glossary initialization warning: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Junior...")

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="""
    ## Junior - Your Trusted AI Legal Assistant

    An Agentic AI Workflow Platform designed for Indian lawyers.

    ### Features

    - **Zero-Hallucination Research**: Every claim linked to specific paragraphs
    - **Traffic Light Shepardizing**: 🟢 Good Law | 🟡 Caution | 🔴 Overruled
    - **Judge Analytics**: Behavioral patterns from past rulings
    - **Multilingual Support**: Query in Hindi, search in English
    - **Court-Ready Formatting**: Auto-format for any Indian court

    ### Privacy

    - DPDP Act Compliant
    - Local PII Redaction
    - AI Draft Watermarking
    """,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Enable Gzip Compression (High Performance)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else ["https://junior.legal"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if FRONTEND_ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_ASSETS_DIR)), name="assets")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions"""
    logger.error(
        f"Unhandled exception: {request.method} {request.url.path}",
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please check logs or try again later."}
    )

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with timing"""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    logger.info(
        f"{request.method} {request.url.path} "
        f"→ {response.status_code} ({duration:.3f}s)"
    )
    return response

# Include API router
app.include_router(api_router)

@app.get("/")
async def frontend_root():
    """Serve the professional frontend."""
    index_path = FRONTEND_DIST_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {
        "message": "Frontend build not found. Run `cd frontend; npm run build`."
    }

@app.get("/{full_path:path}")
async def frontend_spa_fallback(full_path: str):
    """SPA fallback: serve the frontend for non-API deep links."""
    # Let FastAPI handle its own routes first (docs/redoc/openapi/api).
    # This fallback only triggers if no other route matched.
    index_path = FRONTEND_DIST_DIR / "index.html"
    if not index_path.exists():
        return {
            "message": "Frontend build not found. Run `cd frontend; npm run build`."
        }

    # If a real file exists in dist (e.g. favicon), serve it.
    candidate = FRONTEND_DIST_DIR / full_path
    if candidate.is_file():
        return FileResponse(candidate)

    return FileResponse(index_path)

@app.get("/api")
async def api_info():
    """API Information endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "api_base": "/api/v1",
        "docs": "/docs",
        "endpoints": {
            "research": "/api/v1/research",
            "documents": "/api/v1/documents",
            "judges": "/api/v1/judges",
            "cases": "/api/v1/cases",
            "chat": "/api/v1/chat",
            "translate": "/api/v1/translate",
            "format": "/api/v1/format",
            "websocket": "/api/v1/ws/research/{client_id}",
        }
    }

def main():
    """Run the application"""
    import uvicorn

    uvicorn.run(
        "junior.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        log_level="debug" if settings.app_debug else "info",
    )

if __name__ == "__main__":
    main()
