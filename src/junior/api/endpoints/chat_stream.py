"""
Streaming chat endpoint for real-time responses
"""

from uuid import uuid4
from datetime import datetime
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator

from junior.core import get_logger, settings
from junior.services.conversational_chat import ConversationalChat
from junior.api.schemas import ChatRequest, ChatMessage, ChatSession

router = APIRouter()
logger = get_logger(__name__)

# Services
chat_service = ConversationalChat()

# Import shared session store from chat.py
from . import chat
active_sessions = chat.active_sessions


async def stream_chat_response(request: ChatRequest) -> AsyncGenerator[str, None]:
    """
    Stream chat response in Server-Sent Events (SSE) format
    """
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

        # Send session ID first
        yield f"data: {json.dumps({'type': 'session', 'session_id': session.id})}\n\n"

        # API key check
        if not settings.perplexity_api_key and not settings.groq_api_key:
            error_msg = "⚠️ No API key configured. Please add Perplexity or Groq API key to settings."
            yield f"data: {json.dumps({'type': 'chunk', 'content': error_msg})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        # Get conversation history (last 6 messages for context)
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in session.messages[-7:-1]  # Exclude the message we just added
        ]
        
        # Stream response chunks
        full_response = ""
        async for chunk in chat_service.stream_response(
            request.message,
            conversation_history,
            use_research=False
        ):
            full_response += chunk
            # Send each chunk to frontend
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
        
        # Save assistant message to session
        assistant_message = ChatMessage(
            id=str(uuid4()),
            role="assistant",
            content=full_response.strip(),
            citations=[],
            timestamp=datetime.utcnow(),
        )
        session.messages.append(assistant_message)
        session.updated_at = datetime.utcnow()

        # Send done signal
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as e:
        logger.error(f"Streaming chat error: {e}", exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream chat responses in real-time (Server-Sent Events)
    """
    logger.info(f"Streaming chat: {request.message[:50]}...")
    
    return StreamingResponse(
        stream_chat_response(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
