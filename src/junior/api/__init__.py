"""
API module for Junior Legal Assistant
FastAPI endpoints for the web interface
"""

from .router import api_router
from .schemas import (
    ResearchRequest,
    ResearchResponse,
    DocumentUploadResponse,
    ChatMessage,
    ChatSession,
)

__all__ = [
    "api_router",
    "ResearchRequest",
    "ResearchResponse",
    "DocumentUploadResponse",
    "ChatMessage",
    "ChatSession",
]
