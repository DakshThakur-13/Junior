"""
Chat session management endpoints
Note: Actual chat happens via streaming endpoint in chat_stream.py
"""

from datetime import datetime
import diskcache as dc

from fastapi import APIRouter, HTTPException

from junior.core import get_logger
from junior.api.schemas import ChatMessage, ChatSession

router = APIRouter()
logger = get_logger(__name__)

# In-memory store for demo (use database in production)
# Shared with chat_stream.py
active_sessions: dict[str, ChatSession] = {}
SESSION_CACHE = dc.Cache("./.cache/chat_sessions")


def _serialize_session(session: ChatSession) -> dict:
    return {
        "id": session.id,
        "title": session.title,
        "messages": [m.model_dump(mode="json") for m in session.messages],
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


def _deserialize_session(data: dict) -> ChatSession:
    return ChatSession(
        id=str(data.get("id", "")),
        title=str(data.get("title", "Untitled session")),
        messages=[ChatMessage(**m) for m in data.get("messages", [])],
        created_at=datetime.fromisoformat(data.get("created_at")),
        updated_at=datetime.fromisoformat(data.get("updated_at")),
    )


def save_session(session: ChatSession) -> None:
    active_sessions[session.id] = session
    try:
        SESSION_CACHE[session.id] = _serialize_session(session)
    except Exception:
        logger.warning("Failed to persist chat session %s", session.id)


def delete_session_cache(session_id: str) -> None:
    try:
        if session_id in SESSION_CACHE:
            del SESSION_CACHE[session_id]
    except Exception:
        logger.warning("Failed to delete persisted chat session %s", session_id)


def _load_cached_sessions() -> None:
    try:
        for key in SESSION_CACHE.iterkeys():
            raw = SESSION_CACHE.get(key)
            if not isinstance(raw, dict):
                continue
            try:
                session = _deserialize_session(raw)
                active_sessions[session.id] = session
            except Exception:
                logger.warning("Skipping malformed cached chat session key=%s", key)
    except Exception:
        logger.warning("Unable to load chat sessions from cache")


_load_cached_sessions()


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
        delete_session_cache(session_id)

    return {"status": "deleted", "session_id": session_id}
