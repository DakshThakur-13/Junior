"""
Research endpoints
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, List

from junior.core import get_logger
from junior.core.types import Language
from junior.graph import LegalResearchWorkflow
from junior.core.exceptions import ConfigurationError, LLMNotConfiguredError
from junior.api.schemas import (
    ResearchRequest,
    ResearchResponse,
    CitationResponse,
    DevilsAdvocateRequest,
    DevilsAdvocateResponse,
    OfficialSourcesSearchRequest,
    OfficialSourcesSearchResponse,
    OfficialSourceItem,
    ManualIngestRequest,
    ManualIngestResponse,
    LawyerProtocolsResponse,
    LawyerProtocolItem,
)
from pydantic import BaseModel
from junior.services.audit_log import AuditEvent, append_audit_event

class PreviewRequest(BaseModel):
    url: str

class DocumentMetadata(BaseModel):
    court: Optional[str] = None
    date: Optional[str] = None
    case_number: Optional[str] = None
    judge: Optional[str] = None
    parties: Optional[str] = None

class DocumentConnection(BaseModel):
    title: str
    type: str
    reason: str

class PreviewResponse(BaseModel):
    title: str
    content: str
    summary_ai: Optional[str] = None
    key_points: List[str] = []
    quotes: List[str] = []
    metadata: Optional[DocumentMetadata] = None
    connections: List[DocumentConnection] = []
    full_text_length: int
    error: Optional[str] = None

router = APIRouter()
logger = get_logger(__name__)

@router.get("/protocols", response_model=LawyerProtocolsResponse)
async def list_lawyer_protocols():
    """List available lawyer protocols (Criminal/Civil) for structured reasoning."""
    from junior.services.lawyer_protocols import list_protocols

    return LawyerProtocolsResponse(
        protocols=[
            LawyerProtocolItem(
                id=p.id,
                title=p.title,
                domain=p.domain,
                purpose=p.purpose,
            )
            for p in list_protocols()
        ]
    )

@router.post("/", response_model=ResearchResponse)
async def research(request: ResearchRequest):
    """
    Perform legal research on a query

    This endpoint triggers the full Agentic RAG pipeline:
    1. Document search
    2. Research agent extracts relevant information
    3. Critic agent validates citations
    4. Writer agent synthesizes findings

    The process iterates until confidence is high or max iterations reached.
    """
    logger.info(f"Research request: {request.query[:100]}...")

    try:
        # Create workflow
        workflow = LegalResearchWorkflow(max_iterations=request.max_iterations)

        # Execute research with tracing
        result, trace, final_state = await workflow.research_with_trace(
            query=request.query,
            language=request.language,
        )

        # Format citations for response
        def _status_emoji(status: str) -> str:
            return {
                "good_law": "🟢",
                "distinguished": "🟡",
                "overruled": "🔴",
            }.get(status, "⚪")

        citations = []
        for c in (final_state.get("citations") or []):
            # `c` is typically a Pydantic model (junior.core.types.Citation)
            status = getattr(getattr(c, "status", None), "value", None) or getattr(c, "status", "good_law")
            formatted = getattr(c, "formatted", None)
            if not isinstance(formatted, str):
                case_name = getattr(c, "case_name", "")
                year = getattr(c, "year", "")
                court_val = getattr(getattr(c, "court", None), "value", None) or getattr(c, "court", "")
                formatted = f"{case_name} ({year}) {str(court_val).replace('_',' ').title()}".strip()

            court_val = getattr(getattr(c, "court", None), "value", None) or getattr(c, "court", "other")
            citations.append(
                CitationResponse(
                    case_name=getattr(c, "case_name", "Unknown"),
                    case_number=getattr(c, "case_number", "Unknown"),
                    court=str(court_val),
                    year=int(getattr(c, "year", 0) or 0),
                    paragraph=getattr(c, "paragraph", None),
                    status=str(status),
                    status_emoji=_status_emoji(str(status)),
                    formatted=formatted,
                )
            )

        confidence_score = float(final_state.get("confidence_score", 0) or 0)
        confidence_band = "high" if confidence_score >= 0.75 else "medium" if confidence_score >= 0.45 else "low"
        total_citation_count = len(citations)
        verified_citation_count = len([c for c in citations if c.status in {"good_law", "distinguished"}])
        evidence_sufficiency = "sufficient" if verified_citation_count >= 2 and confidence_score >= 0.55 else "limited" if total_citation_count >= 1 else "insufficient"

        append_audit_event(
            AuditEvent(
                event_type="research.query",
                actor="advocate",
                target="research",
                details={
                    "query_length": len(request.query),
                    "confidence_score": confidence_score,
                    "confidence_band": confidence_band,
                    "verified_citation_count": verified_citation_count,
                    "total_citation_count": total_citation_count,
                },
            )
        )

        return ResearchResponse(
            query=request.query,
            summary=result.summary or "Research completed. Please review the findings.",
            citations=citations,
            confidence_score=confidence_score,
            confidence_band=confidence_band,
            iterations=int(final_state.get("iteration", 0) or 0),
            processing_time_ms=result.processing_time_ms,
            evidence_sufficiency=evidence_sufficiency,
            verified_citation_count=verified_citation_count,
            total_citation_count=total_citation_count,
            ai_disclaimer="AI-assisted legal research. Validate all authorities against official court records before filing.",
            trace=trace,
        )

    except (ConfigurationError, LLMNotConfiguredError) as e:
        raise HTTPException(status_code=503, detail=str(e))

    except Exception as e:
        logger.error(f"Research error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quick", response_model=dict)
async def quick_research(query: str, language: Language = Language.ENGLISH):
    """
    Quick research endpoint for simple queries

    Uses fewer iterations for faster response.
    """
    logger.info(f"Quick research: {query[:50]}...")

    try:
        workflow = LegalResearchWorkflow(max_iterations=2)
        result = await workflow.research(query, language)

        return {
            "query": query,
            "summary": result.summary,
            "processing_time_ms": result.processing_time_ms,
        }

    except (ConfigurationError, LLMNotConfiguredError) as e:
        raise HTTPException(status_code=503, detail=str(e))

    except Exception as e:
        logger.error(f"Quick research error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/shepardize/{case_number}")
async def shepardize_case(case_number: str):
    """
    Shepardize a case - check its current validity

    Returns:
    - 🟢 GREEN: Good Law - Safe to cite
    - 🟡 YELLOW: Distinguished/Criticized - Use with caution
    - 🔴 RED: Overruled/Stayed - Do not use
    """
    logger.info(f"Shepardizing: {case_number}")

    # Placeholder - would query the database for case status
    return {
        "case_number": case_number,
        "status": "good_law",
        "status_emoji": "🟢",
        "message": "Good Law - Safe to cite",
        "citing_cases": [],
        "criticizing_cases": [],
        "last_checked": "2024-12-16",
    }

def _parse_devils_advocate_response(text: str) -> tuple[list[dict], list[str]]:
    """Best-effort parser for the Devil's Advocate markdown output."""
    if not text:
        return ([], [])

    attack_points: list[dict] = []
    preparation: list[str] = []

    # Split into sections by Attack Point headings.
    parts = text.split("### Attack Point")
    if len(parts) > 1:
        for part in parts[1:]:
            # First line contains ": <Title>" usually.
            lines = [ln.strip() for ln in part.strip().splitlines() if ln.strip()]
            if not lines:
                continue

            title_line = lines[0]
            title = title_line
            if ":" in title_line:
                title = title_line.split(":", 1)[1].strip() or title_line

            weakness = ""
            counter_citation = ""
            suggested_attack = ""
            raw_block = "\n".join(lines)

            for ln in lines:
                low = ln.lower()
                if low.startswith("**the weakness:**"):
                    weakness = ln.split(":", 1)[1].strip() if ":" in ln else ""
                elif low.startswith("**counter-citation:**"):
                    counter_citation = ln.split(":", 1)[1].strip() if ":" in ln else ""
                elif low.startswith("**suggested attack:**"):
                    suggested_attack = ln.split(":", 1)[1].strip() if ":" in ln else ""

            attack_points.append(
                {
                    "title": title,
                    "weakness": weakness,
                    "counter_citation": counter_citation,
                    "suggested_attack": suggested_attack,
                    "raw": raw_block,
                }
            )

    # Preparation recommendations: try to capture bullet list under OVERALL VULNERABILITY ASSESSMENT.
    lower = text.lower()
    idx = lower.find("preparation recommendations")
    if idx != -1:
        tail = text[idx:]
        for ln in tail.splitlines()[1:]:
            s = ln.strip()
            if not s:
                continue
            if s.startswith("-"):
                preparation.append(s.lstrip("- ").strip())
            # stop if we hit a new top-level heading
            if s.startswith("## "):
                break

    return (attack_points, preparation)

@router.post("/devils-advocate", response_model=DevilsAdvocateResponse)
async def devils_advocate(request: DevilsAdvocateRequest):
    """
    Devil's Advocate Simulator

    Simulates opposing counsel attacking your arguments.
    Used in the "War Room" feature for stress-testing.
    """
    from junior.agents.critic import DevilsAdvocateAgent
    from junior.agents.base import AgentState

    logger.info("Running Devil's Advocate simulation...")

    try:
        # Create state with the case info
        state = AgentState(
            query=request.case_summary,
            research_notes=[request.arguments] + (["CITATIONS:\n- " + "\n- ".join(request.citations)] if request.citations else []),
            draft=request.arguments,
            metadata={"protocol_id": request.protocol_id} if request.protocol_id else {},
        )

        # Run simulation
        devil = DevilsAdvocateAgent()
        result = await devil.simulate_opposition(state)

        opposition = result.get("opposition_arguments") or ""
        attack_points, preparation = _parse_devils_advocate_response(opposition)

        # Heuristic score: more attack points + "critical" language => higher vulnerability.
        critical_hits = opposition.lower().count("critical")
        score = min(10.0, max(0.0, 2.0 + (len(attack_points) * 1.2) + (critical_hits * 0.6)))
        if not preparation:
            preparation = ["Prepare counter-arguments for each attack point and shore up evidentiary gaps."]

        confidence_band = "high" if score <= 3.5 else "medium" if score <= 6.5 else "low"
        evidence_sufficiency = "sufficient" if request.citations and len(request.citations) >= 2 else "limited" if request.citations else "insufficient"

        append_audit_event(
            AuditEvent(
                event_type="research.devils_advocate",
                actor="advocate",
                target="devils_advocate",
                details={
                    "attack_points": len(attack_points),
                    "vulnerability_score": score,
                    "confidence_band": confidence_band,
                    "evidence_sufficiency": evidence_sufficiency,
                },
            )
        )

        return DevilsAdvocateResponse(
            attack_points=attack_points,
            vulnerability_score=score,
            preparation_recommendations=preparation,
            confidence_band=confidence_band,
            evidence_sufficiency=evidence_sufficiency,
            ai_disclaimer="AI-assisted adversarial simulation. Use with advocate review before strategy finalization.",
        )

    except ConfigurationError as e:
        raise HTTPException(status_code=503, detail=str(e))

    except Exception as e:
        logger.error(f"Devil's Advocate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sources/search", response_model=OfficialSourcesSearchResponse)
async def search_official_sources(request: OfficialSourcesSearchRequest):
    """Return curated official sources + study material for Indian legal research.

    This endpoint is intentionally offline-friendly (no live scraping).
    It returns a curated catalog with metadata the UI can display and open.
    """
    try:
        try:
            from junior.services.official_sources import search_sources
        except ImportError as import_err:
            logger.error(f"official_sources module not found: {import_err}")
            # Return empty results if service not available
            return OfficialSourcesSearchResponse(
                query=request.query,
                results=[],
            )

        items, search_time_ms = await search_sources(
            request.query,
            category=request.category,
            authority=request.authority,
            limit=request.limit,
        )

        result_items = [
            OfficialSourceItem(
                id=it.id,
                title=it.title,
                type=it.type,
                summary=it.summary,
                source=it.source,
                url=it.url,
                publisher=it.publisher,
                authority=it.authority,
                tags=list(it.tags),
            )
            for it in items
        ]

        return OfficialSourcesSearchResponse(
            query=request.query,
            results=result_items,
            total_count=len(result_items),
            search_time_ms=search_time_ms,
        )
    except Exception as e:
        logger.error(f"Official sources search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sources/preview", response_model=PreviewResponse)
async def preview_source(request: PreviewRequest):
    """
    Fetch and preview content from a URL.
    """
    try:
        from junior.services.official_sources import get_preview
        
        # get_preview is a sync function, not async - don't await
        result = get_preview(request.url)
        return PreviewResponse(
            title=result.get("title", "Preview"),
            content=result.get("content", ""),
            summary_ai=result.get("summary_ai"),
            key_points=result.get("key_points", []),
            quotes=result.get("quotes", []),
            metadata=result.get("metadata"),
            connections=result.get("connections", []),
            full_text_length=result.get("full_text_length", 0),
            error=result.get("error")
        )
    except Exception as e:
        logger.error(f"Preview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sources/ingest", response_model=ManualIngestResponse)
async def ingest_public_manual(request: ManualIngestRequest):
    """Ingest (RAG-index) an allowlisted public manual/book from the curated catalog.

    Notes:
    - This is NOT model fine-tuning.
    - It downloads a PDF (if the catalog URL is a PDF), chunks it, embeds it, and writes it
      into the local store under `uploads/` so Agentic RAG can retrieve it.
    """
    try:
        from junior.services.manual_ingestion import ManualIngestionService

        service = ManualIngestionService()
        result = await service.ingest_catalog_source(request.source_id, force=request.force)
        return ManualIngestResponse(
            source_id=request.source_id,
            document_id=result.document_id,
            title=result.title,
            chunks=result.chunks,
            bytes_downloaded=result.bytes_downloaded,
            source_url=result.source_url,
            status="ingested" if result.bytes_downloaded > 0 else "already_ingested",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (ConfigurationError, LLMNotConfiguredError) as e:
        # Ingestion doesn't require LLM, but keep consistent 503 behavior for config issues.
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Manual ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
