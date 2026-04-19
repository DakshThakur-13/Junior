"""
Streaming chat endpoint for real-time responses
"""

from uuid import uuid4
from datetime import datetime
import json
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator

from junior.core import get_logger, settings
from junior.core.types import Language
from junior.services.conversational_chat import ConversationalChat
from junior.services.translator import TranslationService
from junior.api.schemas import ChatRequest, ChatMessage, ChatSession

router = APIRouter()
logger = get_logger(__name__)

# Services
chat_service = ConversationalChat()

# Import shared session store from chat.py
from . import chat
active_sessions = chat.active_sessions


URL_RE = re.compile(r"https?://[^\s)\]>]+", re.IGNORECASE)
LEGAL_CITATION_RE = re.compile(
    r"\b(?:AIR\s+\d{4}\s+[A-Z]{2,}\s+\d+|\(\d{4}\)\s*\d+\s*SCC\s*\d+|\d{4}\s*\(\d+\)\s*SCR\s*\d+|\bSCC\s*OnLine\s*\w+\s*\d+|\b\d{4}\s*\d+\s*SCR\s*\d+)\b",
    re.IGNORECASE,
)


def _extract_sources(text: str) -> list[str]:
    sources: list[str] = []
    seen: set[str] = set()
    for m in URL_RE.findall(text or ""):
        cleaned = m.rstrip(".,;:!?")
        if cleaned not in seen:
            seen.add(cleaned)
            sources.append(cleaned)
    return sources[:5]


def _extract_legal_citations(text: str) -> list[str]:
    citations: list[str] = []
    seen: set[str] = set()
    for match in LEGAL_CITATION_RE.findall(text or ""):
        cleaned = " ".join(match.split())
        if cleaned not in seen:
            seen.add(cleaned)
            citations.append(cleaned)
    return citations[:8]


def _suggest_next_actions(user_message: str, final_response: str) -> list[str]:
    msg = (user_message or "").lower()
    resp = (final_response or "").lower()
    actions: list[str] = []

    if any(k in msg for k in ["bail", "anticipatory", "hearing", "court"]):
        actions.append("Create a hearing checklist with dates, documents, and witness prep.")
    if any(k in msg for k in ["draft", "petition", "notice", "application"]):
        actions.append("Draft a filing-ready version with court formatting and missing fields highlighted.")
    if "evidence" in msg or "evidence" in resp:
        actions.append("List evidence gaps and priority documents to collect before filing.")
    if any(k in msg for k in ["section", "act", "precedent", "judgment"]):
        actions.append("Pull 3 stronger precedents and explain how each supports your facts.")

    if not actions:
        actions = [
            "Summarize this advice into an actionable checklist.",
            "Highlight risks and counter-arguments I should prepare for.",
            "Draft the next formal legal document based on this chat.",
        ]

    return actions[:3]


def _has_devanagari(text: str) -> bool:
    return any("\u0900" <= c <= "\u097F" for c in (text or ""))


def _looks_romanized_indic(text: str) -> bool:
    """Best-effort heuristic for Hinglish-style Roman input.

    We only attempt transliteration when the user explicitly chose an Indic input
    language (hi/mr) AND the text looks like romanization, not ordinary English.
    """
    s = (text or "").strip()
    if not s or len(s) < 3:
        return False
    if _has_devanagari(s):
        return False

    ascii_letters = sum(1 for c in s if ("a" <= c.lower() <= "z"))
    total = max(1, len(s))
    if (ascii_letters / total) < 0.6:
        return False

    markers = [
        "aa",
        "ii",
        "uu",
        "kh",
        "gh",
        "ch",
        "jh",
        "th",
        "dh",
        "bh",
        "sh",
        "ny",
        "gy",
        "kya",
        "kyu",
        "nahi",
        "nhi",
        "hai",
        "hoga",
        "kr",
    ]
    sl = s.lower()
    return any(m in sl for m in markers)


def _roman_to_devanagari_best_effort(text: str) -> str:
    """Attempt Roman → Devanagari transliteration (HK / ITRANS)."""
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
    except Exception:
        return text

    s = text or ""

    candidates: list[str] = []
    try:
        candidates.append(transliterate(s, sanscript.HK, sanscript.DEVANAGARI))
    except Exception:
        pass
    try:
        candidates.append(transliterate(s, sanscript.ITRANS, sanscript.DEVANAGARI))
    except Exception:
        pass

    def score(t: str) -> int:
        return sum(1 for c in (t or "") if "\u0900" <= c <= "\u097F")

    best = s
    best_score = score(s)
    for c in candidates:
        sc = score(c)
        if sc > best_score:
            best, best_score = c, sc

    # Require a minimal signal; otherwise likely English text.
    return best if best_score >= 3 else s


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
            chat.save_session(session)

        translator = TranslationService()

        # Translate user input to English if needed (supports Roman-script Hindi/Marathi via heuristic transliteration)
        input_lang = request.input_language or translator.detect_language(request.message)
        message_for_model = request.message
        if input_lang in {Language.HINDI, Language.MARATHI} and _looks_romanized_indic(message_for_model):
            message_for_model = _roman_to_devanagari_best_effort(message_for_model)

        if input_lang != Language.ENGLISH:
            try:
                q = await translator.translate_query(
                    message_for_model,
                    source_lang=input_lang,
                    target_lang=Language.ENGLISH,
                )
                message_for_model = q.translated_text
            except Exception as e:
                logger.warning(f"Input translation failed; using original message. Error: {e}")

        # Add user message (store original)
        user_message = ChatMessage(
            id=str(uuid4()),
            role="user",
            content=request.message,
            timestamp=datetime.utcnow(),
        )
        session.messages.append(user_message)
        chat.save_session(session)

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
        full_response_en = ""
        should_stream_english = request.language == Language.ENGLISH

        use_research = request.use_research
        if use_research is None:
            use_research = chat_service.should_use_deep_research(message_for_model)

        async for chunk in chat_service.stream_response(
            message_for_model,
            conversation_history,
            use_research=use_research,
        ):
            full_response_en += chunk
            if should_stream_english:
                # Send each chunk to frontend
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

        final_response = full_response_en.strip()
        preserved_terms: list[str] = []

        if not should_stream_english:
            # Translate once at the end (keeps SSE simple and avoids per-chunk translation artifacts)
            try:
                tr = await translator.translate_response(
                    text=final_response,
                    target_lang=request.language,
                    preserve_legal_terms=True,
                )
                final_response = tr.translated_text
                preserved_terms = tr.preserved_terms

                if request.output_script == "roman" and request.language in {Language.HINDI, Language.MARATHI}:
                    try:
                        from indic_transliteration import sanscript
                        from indic_transliteration.sanscript import transliterate

                        # Harvard-Kyoto: ASCII-only romanization (no diacritics)
                        final_response = transliterate(final_response, sanscript.DEVANAGARI, sanscript.HK)
                    except Exception as e:
                        logger.warning(f"Romanization failed; returning native script. Error: {e}")
            except Exception as e:
                logger.warning(f"Output translation failed; returning English. Error: {e}")
                final_response = full_response_en.strip()

            if not preserved_terms:
                try:
                    preserved_terms = translator._find_preserved_terms(final_response)
                except Exception:
                    preserved_terms = []

            yield f"data: {json.dumps({'type': 'chunk', 'content': final_response})}\n\n"
            yield f"data: {json.dumps({'type': 'meta', 'preserved_terms': preserved_terms})}\n\n"
        else:
            # English streaming path: emit preserved terms after full response is known.
            try:
                preserved_terms = translator._find_preserved_terms(final_response)
            except Exception:
                preserved_terms = []
            yield f"data: {json.dumps({'type': 'meta', 'preserved_terms': preserved_terms})}\n\n"

        sources = _extract_sources(final_response)
        legal_citations = _extract_legal_citations(final_response)
        suggested_actions = _suggest_next_actions(request.message, final_response) if request.suggest_actions else []
        yield f"data: {json.dumps({'type': 'meta', 'sources': sources, 'citations': legal_citations, 'suggested_actions': suggested_actions})}\n\n"
        
        # Save assistant message to session
        assistant_message = ChatMessage(
            id=str(uuid4()),
            role="assistant",
            content=final_response,
            citations=[],
            timestamp=datetime.utcnow(),
        )
        session.messages.append(assistant_message)
        session.updated_at = datetime.utcnow()
        chat.save_session(session)

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
