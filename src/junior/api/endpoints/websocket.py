"""
WebSocket endpoint for real-time streaming responses
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import asyncio
from uuid import uuid4

from junior.core.config import get_settings
from junior.core.logging import get_logger
from junior.core.types import Language
from junior.graph.workflow import LegalResearchWorkflow

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()

# Active connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_connections: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_message(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)
    
    async def broadcast(self, session_id: str, message: dict):
        if session_id in self.session_connections:
            for client_id in self.session_connections[session_id]:
                await self.send_message(client_id, message)


manager = ConnectionManager()


@router.websocket("/ws/research/{client_id}")
async def websocket_research(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for streaming research responses.
    
    Message Protocol:
    - Client sends: {"type": "query", "query": "...", "language": "en", "session_id": "..."}
    - Server sends: {"type": "status", "status": "researching", "node": "researcher"}
    - Server sends: {"type": "chunk", "content": "...", "node": "writer"}
    - Server sends: {"type": "citation", "citation": {...}}
    - Server sends: {"type": "trace", "step": {...}}
    - Server sends: {"type": "complete", "summary": "...", "citations": [...]}
    - Server sends: {"type": "error", "message": "..."}
    """
    await manager.connect(websocket, client_id)
    
    try:
        workflow = LegalResearchWorkflow()
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "query":
                query = message.get("query", "")
                language = message.get("language", "en")
                session_id = message.get("session_id", str(uuid4()))
                
                # Send initial status
                await manager.send_message(client_id, {
                    "type": "status",
                    "status": "starting",
                    "session_id": session_id
                })
                
                try:
                    # Run workflow with streaming callbacks
                    async for event in stream_workflow(workflow, query, language, client_id):
                        await manager.send_message(client_id, event)
                    
                except Exception as e:
                    logger.error(f"Workflow error: {e}")
                    await manager.send_message(client_id, {
                        "type": "error",
                        "message": str(e)
                    })
            
            elif message.get("type") == "ping":
                await manager.send_message(client_id, {"type": "pong"})
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(client_id)


async def stream_workflow(workflow: LegalResearchWorkflow, query: str, language: str, client_id: str):
    """
    Stream workflow execution events.
    """
    import time
    from junior.agents.base import AgentState

    # Validate language
    try:
        lang_enum = Language(language)
    except Exception:
        lang_enum = Language.ENGLISH

    start_time = time.time()
    trace_logs = []
    latest_state: dict = {}
    last_draft: str = ""
    citations_sent: set[str] = set()

    initial_state = AgentState(
        query=query,
        language=lang_enum.value,
        max_iterations=workflow.max_iterations,
    )

    # Stream node execution from the real LangGraph
    async for event in workflow._graph.astream(initial_state):
        node_name = list(event.keys())[0]
        node_state = event[node_name]

        if isinstance(node_state, dict):
            latest_state = node_state

        # Emit status per node
        yield {
            "type": "status",
            "status": "processing",
            "node": node_name,
            "iteration": int(getattr(node_state, "iteration", 0) or node_state.get("iteration", 0) or 0),
        }

        # Emit trace step
        trace_step = {
            "node": node_name,
            "timestamp": time.time() - start_time,
            "iteration": node_state.get("iteration", 0) if isinstance(node_state, dict) else 0,
            "citations_count": len(node_state.get("citations", [])) if isinstance(node_state, dict) else 0,
            "confidence": node_state.get("confidence_score", 0) if isinstance(node_state, dict) else 0,
            "needs_revision": node_state.get("needs_revision", False) if isinstance(node_state, dict) else False,
        }
        trace_logs.append(trace_step)
        yield {"type": "trace", "step": trace_step}

        # Best-effort incremental output streaming (writer drafts)
        if isinstance(node_state, dict) and node_name == "write":
            draft = node_state.get("draft") or ""
            if isinstance(draft, str) and len(draft) > len(last_draft):
                delta = draft[len(last_draft) :]
                last_draft = draft
                if delta.strip():
                    yield {"type": "chunk", "content": delta, "node": "writer"}

        # Emit citations as they appear
        if isinstance(node_state, dict):
            for c in node_state.get("citations", []) or []:
                # Hashable-ish key
                key = json.dumps(c, sort_keys=True, default=str)
                if key in citations_sent:
                    continue
                citations_sent.add(key)
                yield {"type": "citation", "citation": c}

    # Final output
    final_output = latest_state.get("final_output") or latest_state.get("draft") or ""

    # Translate if needed (IndicTrans2 preferred in TranslationService)
    if lang_enum != Language.ENGLISH and final_output:
        try:
            from junior.services import TranslationService
            translator = TranslationService()
            tr = await translator.translate_response(
                text=str(final_output),
                target_lang=lang_enum,
                preserve_legal_terms=True,
            )
            final_output = tr.translated_text
        except Exception as e:
            logger.error(f"WebSocket translation failed: {e}")

    yield {
        "type": "complete",
        "summary": final_output or "Research complete.",
        "citations": latest_state.get("citations", []) or [],
        "trace": trace_logs,
    }


@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time chat within a research session.
    Supports follow-up questions and context-aware responses.
    """
    client_id = f"chat-{session_id}-{uuid4().hex[:8]}"
    await manager.connect(websocket, client_id)
    
    # Add to session connections
    if session_id not in manager.session_connections:
        manager.session_connections[session_id] = set()
    manager.session_connections[session_id].add(client_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "message":
                content = message.get("content", "")
                
                # Echo to all session participants
                await manager.broadcast(session_id, {
                    "type": "message",
                    "sender": client_id,
                    "content": content,
                    "timestamp": asyncio.get_event_loop().time()
                })
                
                # If it's a question, trigger AI response
                if content.strip().endswith("?"):
                    await manager.send_message(client_id, {
                        "type": "typing",
                        "sender": "assistant"
                    })
                    
                    # Generate response (simplified)
                    await asyncio.sleep(1)
                    await manager.send_message(client_id, {
                        "type": "message",
                        "sender": "assistant",
                        "content": f"I understand you're asking about '{content}'. Based on my research...",
                        "timestamp": asyncio.get_event_loop().time()
                    })
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        if session_id in manager.session_connections:
            manager.session_connections[session_id].discard(client_id)
