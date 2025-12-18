"""
Chat endpoints
"""

from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import Optional

from junior.core import get_logger, settings
from junior.core.types import Language
from junior.graph import LegalResearchWorkflow
from junior.db import ChatRepository
from junior.core.exceptions import ConfigurationError, LLMNotConfiguredError
from junior.api.schemas import (
    ChatRequest,
    ChatResponse,
    ChatMessage,
    ChatSession,
)

router = APIRouter()
logger = get_logger(__name__)

# In-memory store for demo (use database in production)
active_sessions: dict[str, ChatSession] = {}

@router.post("/", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    Send a message in a chat session

    Creates a new session if session_id is not provided.
    """
    logger.info(f"Chat message: {request.message[:50]}...")

    session: Optional[ChatSession] = None

    try:
        # Get or create session
        if request.session_id and request.session_id in active_sessions:
            session = active_sessions[request.session_id]
        else:
            session_id = str(uuid4())
            session = ChatSession(
                id=session_id,
                title=request.message[:50] + "...",
                messages=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            active_sessions[session_id] = session

        # Add user message
        user_message = ChatMessage(
            id=str(uuid4()),
            role="user",
            content=request.message,
            timestamp=datetime.utcnow(),
        )
        session.messages.append(user_message)

        # Pick a lawyer protocol (optional). If not provided, use a heuristic.
        from junior.services.lawyer_protocols import suggest_protocol_id, protocol_brief

        protocol_id = request.protocol_id or suggest_protocol_id(request.message)

        # Fast, safe fallback: if no LLM is configured, avoid running the workflow at all.
        # This prevents long hangs from embeddings/model initialization and keeps the UX stable.
        if not settings.groq_api_key and not settings.huggingface_api_key:
            brief = protocol_brief(protocol_id).strip() if protocol_id else ""
            assistant_message = ChatMessage(
                id=str(uuid4()),
                role="assistant",
                content=(
                    "LLM is not configured, so I cannot run full AI research right now.\n\n"
                    "I can still help you proceed safely:\n"
                    "- Use the Research tab to open OFFICIAL sources, and\n"
                    "- Upload case documents to build a cited record.\n\n"
                    + (f"{brief}\n" if brief else "")
                    + "Share FIR/complaint + key dates + relief sought, and I will generate a checklist and next-step plan."
                ),
                citations=[],
                timestamp=datetime.utcnow(),
            )
            session.messages.append(assistant_message)
            session.updated_at = datetime.utcnow()

            return ChatResponse(
                session_id=session.id,
                message=assistant_message,
                related_documents=[],
            )

        # Process with research workflow (and keep trace to extract citations).
        workflow = LegalResearchWorkflow(max_iterations=2)
        result, _trace, final_state = await workflow.research_with_trace(
            query=request.message,
            language=request.language,
        )

        # Map citations into API schema (best-effort, same strategy as research endpoint).
        def _status_emoji(status: str) -> str:
            return {
                "good_law": "🟢",
                "distinguished": "🟡",
                "overruled": "🔴",
            }.get(status, "⚪")

        citations = []
        for c in (final_state.get("citations") or []):
            status = getattr(getattr(c, "status", None), "value", None) or getattr(c, "status", "good_law")
            formatted = getattr(c, "formatted", None)
            if not isinstance(formatted, str):
                case_name = getattr(c, "case_name", "")
                year = getattr(c, "year", "")
                court_val = getattr(getattr(c, "court", None), "value", None) or getattr(c, "court", "")
                formatted = f"{case_name} ({year}) {str(court_val).replace('_',' ').title()}".strip()

            court_val = getattr(getattr(c, "court", None), "value", None) or getattr(c, "court", "other")
            citations.append(
                {
                    "case_name": getattr(c, "case_name", "Unknown"),
                    "case_number": getattr(c, "case_number", "Unknown"),
                    "court": str(court_val),
                    "year": int(getattr(c, "year", 0) or 0),
                    "paragraph": getattr(c, "paragraph", None),
                    "status": str(status),
                    "status_emoji": _status_emoji(str(status)),
                    "formatted": formatted,
                }
            )

        summary = result.summary or ""

        # Evidence-first guard: no citations => no confident conclusion.
        if not citations:
            brief = protocol_brief(protocol_id).strip() if protocol_id else ""
            summary = (
                "I can help, but I cannot give a reliable legal conclusion without verified sources/citations from your library.\n\n"
                "Next best step:\n"
                "- Upload the FIR/complaint, remand orders, charge-sheet (if filed), and any key annexures; or\n"
                "- Use the Research tab to open OFFICIAL sources and add materials to your library.\n\n"
                + (f"{brief}\n" if brief else "")
                + "Reply with the missing facts and documents, and I will produce a court-ready, cited answer."
            )

        # Create assistant response
        assistant_message = ChatMessage(
            id=str(uuid4()),
            role="assistant",
            content=summary or "I couldn't find relevant information for your query.",
            citations=citations,
            timestamp=datetime.utcnow(),
        )
        session.messages.append(assistant_message)
        session.updated_at = datetime.utcnow()

        return ChatResponse(
            session_id=session.id,
            message=assistant_message,
            related_documents=[],
        )

    except (ConfigurationError, LLMNotConfiguredError) as e:
        # Return a helpful, protocol-driven response (HTTP 200) even when LLM is not configured.
        from junior.services.lawyer_protocols import suggest_protocol_id, protocol_brief

        # Ensure a session exists so the response shape is stable.
        if session is None:
            session_id = str(uuid4())
            session = ChatSession(
                id=session_id,
                title=request.message[:50] + "...",
                messages=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            active_sessions[session_id] = session

        protocol_id = request.protocol_id or suggest_protocol_id(request.message)
        brief = protocol_brief(protocol_id).strip() if protocol_id else ""

        assistant_message = ChatMessage(
            id=str(uuid4()),
            role="assistant",
            content=(
                "LLM is not configured, so I cannot run full AI research right now.\n\n"
                "I can still help you proceed safely:\n"
                "- Use the Research tab to open OFFICIAL sources, and\n"
                "- Upload case documents to build a cited record.\n\n"
                + (f"{brief}\n" if brief else "")
                + "If you share FIR/complaint + key dates + relief sought, I will generate a checklist and next-step plan."
            ),
            citations=[],
            timestamp=datetime.utcnow(),
        )

        return ChatResponse(
            session_id=session.id,
            message=assistant_message,
            related_documents=[],
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions", response_model=list[dict])
async def list_sessions(user_id: Optional[str] = None, limit: int = 20):
    """
    List recent chat sessions
    """
    sessions = list(active_sessions.values())
    sessions.sort(key=lambda s: s.updated_at, reverse=True)

    return [
        {
            "id": s.id,
            "title": s.title,
            "message_count": len(s.messages),
            "updated_at": s.updated_at.isoformat(),
        }
        for s in sessions[:limit]
    ]

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

@router.websocket("/ws/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time chat

    Enables streaming responses and real-time updates.
    """
    await websocket.accept()
    logger.info(f"WebSocket connected: {session_id}")

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message = data.get("message", "")
            language = Language(data.get("language", "en"))

            logger.info(f"WS message: {message[:50]}...")

            # Send acknowledgment
            await websocket.send_json({
                "type": "ack",
                "status": "processing",
            })

            # Process with workflow
            workflow = LegalResearchWorkflow(max_iterations=2)

            # Stream intermediate results
            async for event in workflow._graph.astream(
                {"query": message, "language": language.value}
            ):
                node_name = list(event.keys())[0]
                await websocket.send_json({
                    "type": "progress",
                    "node": node_name,
                    "status": "completed",
                })

            # Send final result
            await websocket.send_json({
                "type": "response",
                "content": "Research completed. [Full response would be here]",
                "citations": [],
            })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1000)
