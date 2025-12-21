"""
Chat session management endpoints
Note: Actual chat happens via streaming endpoint in chat_stream.py
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException

from junior.core import get_logger
from junior.api.schemas import ChatSession

router = APIRouter()
logger = get_logger(__name__)

# In-memory store for demo (use database in production)
# Shared with chat_stream.py
active_sessions: dict[str, ChatSession] = {}


@router.get("/sessions")
async def list_sessions():
    """
    List all active chat sessions
    """
    return {
        "sessions": [
            {
                "id": s.id,
                "title": s.title,
                "message_count": len(s.messages),
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in active_sessions.values()
        ]
    }


@router.get("/sessions/{session_id}", response_model=ChatSession)
async def get_session(session_id: str):
    """
    Get a specific chat session with all messages
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    return active_sessions[session_id]


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a chat session
    """
    if session_id in active_sessions:
        del active_sessions[session_id]

    return {"status": "deleted", "session_id": session_id}
