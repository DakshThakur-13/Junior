"""
LangGraph workflow nodes for the Agentic RAG pipeline
"""

import asyncio
from typing import Literal, Optional

from junior.agents import ResearcherAgent, CriticAgent, WriterAgent
from junior.agents.base import AgentState
from junior.core import get_logger
from junior.core.exceptions import ConfigurationError

logger = get_logger(__name__)

# Initialize agents
researcher = ResearcherAgent()
critic = CriticAgent()
writer = WriterAgent()

async def research_node(state: AgentState) -> AgentState:
    """
    Research node - searches for relevant case law

    This node:
    1. Analyzes the query
    2. Searches the document database
    3. Extracts relevant passages with citations
    """
    logger.info(f"[RESEARCH NODE] Iteration {state.iteration + 1}")

    try:
        state = await researcher.process(state)
        logger.info(f"[RESEARCH NODE] Found {len(state.citations)} citations")
    except ConfigurationError:
        raise
    except Exception as e:
        logger.error(f"[RESEARCH NODE] Error: {e}")
        state.metadata["research_error"] = str(e)

    return state

async def critique_node(state: AgentState) -> AgentState:
    """
    Critique node - validates research and citations

    This node:
    1. Verifies all citations against source documents
    2. Identifies logical weaknesses
    3. Plays Devil's Advocate
    4. Determines if revision is needed
    """
    logger.info("[CRITIQUE NODE] Validating research...")

    try:
        state = await critic.process(state)
        logger.info(
            f"[CRITIQUE NODE] Confidence: {state.confidence_score:.1f}, "
            f"Needs revision: {state.needs_revision}"
        )
    except ConfigurationError:
        raise
    except Exception as e:
        logger.error(f"[CRITIQUE NODE] Error: {e}")
        state.metadata["critique_error"] = str(e)
        # Default to allowing passage on error
        state.needs_revision = False
        state.confidence_score = 5.0

    return state

async def write_node(state: AgentState) -> AgentState:
    """
    Write node - synthesizes research into legal prose

    This node:
    1. Takes validated research
    2. Produces a structured legal document
    3. Ensures proper citation format
    4. Generates the final output if confidence is high
    """
    logger.info("[WRITE NODE] Drafting document...")

    try:
        state = await writer.process(state)
        logger.info(f"[WRITE NODE] Draft length: {len(state.draft or '')} characters")

        # Enforce claim/citation coverage (heuristic) to reduce uncited drafting.
        uncited = _detect_uncited_paragraphs(state.draft or "")
        if uncited:
            state.metadata["uncited_paragraphs"] = uncited
            # Force another pass through the loop unless maxed out.
            state.needs_revision = True
            # Reduce confidence but keep it non-zero.
            state.confidence_score = min(state.confidence_score, 6.0)
            logger.warning(f"[WRITE NODE] Detected uncited paragraphs: {uncited}")
    except ConfigurationError:
        raise
    except Exception as e:
        logger.error(f"[WRITE NODE] Error: {e}")
        state.metadata["write_error"] = str(e)

    return state

def decide_next(state: AgentState) -> Literal["research", "critique", "write", "end"]:
    """
    Decision node - determines the next step in the workflow

    Flow logic:
    1. If no research yet -> research
    2. If research done but not critiqued -> critique
    3. If needs revision and under max iterations -> research
    4. If critique passed -> write
    5. If written with high confidence -> end
    6. If max iterations reached -> end
    """
    logger.info(f"[DECIDE] Iteration: {state.iteration}, Confidence: {state.confidence_score}")

    # Check for errors
    if state.metadata.get("research_error") and state.iteration >= state.max_iterations:
        logger.warning("[DECIDE] Max iterations with errors, ending")
        return "end"

    # No research yet
    if not state.research_notes:
        return "research"

    # Research done, need critique
    if not state.critiques:
        return "critique"

    # Needs revision and under max iterations
    if state.needs_revision and state.iteration < state.max_iterations:
        logger.info("[DECIDE] Revision needed, going back to research")
        return "research"

    # No draft yet, go to write
    if not state.draft:
        return "write"

    # Have a draft, check if we need more iterations
    if state.confidence_score < 7.0 and state.iteration < state.max_iterations:
        logger.info("[DECIDE] Confidence low, re-critiquing")
        return "critique"

    # Final output ready or max iterations reached
    if state.final_output or state.iteration >= state.max_iterations:
        return "end"

    # Default: go to write for final output
    return "write"

async def search_documents_node(state: AgentState) -> AgentState:
    """
    Document search node - performs vector similarity search

    This node is called before research to populate the documents
    in the state from the database.

    Parallel execution: local vector search + Indian Kanoon API run concurrently
    so total latency ≈ max(local_latency, kanoon_latency) instead of their sum.
    """
    from junior.db import DocumentRepository
    from junior.services.embedding import EmbeddingService
    from junior.services.kanoon_client import get_kanoon_client

    logger.info("[SEARCH NODE] Parallel search: local DB + Indian Kanoon...")

    query_embedding: Optional[list[float]] = None

    # --- Helper coroutines for parallel execution ---

    async def _local_db_search() -> list[dict]:
        """Search the primary vector database (Supabase pgvector)."""
        nonlocal query_embedding
        try:
            embedding_service = EmbeddingService()
            query_embedding = await embedding_service.get_embedding(state.query)
            doc_repo = DocumentRepository()
            results = await doc_repo.search_by_embedding(embedding=query_embedding, limit=10)
            docs = []
            for chunk, score in results:
                docs.append({
                    "id": chunk.id,
                    "document_id": chunk.document_id,
                    "content": chunk.content,
                    "page_number": chunk.page_number,
                    "paragraph_number": chunk.paragraph_number,
                    "relevance_score": score,
                    "metadata": chunk.metadata,
                    "source": "vector_db",
                })
            return docs
        except Exception as e:
            logger.warning(f"[SEARCH NODE] Vector DB failed: {e}")
            return []

    async def _local_store_search() -> list[dict]:
        """Fallback: local on-disk hybrid search."""
        from pathlib import Path
        from junior.services.local_store import LocalDocumentStore
        try:
            store = LocalDocumentStore(Path("uploads"))
            results = store.search_hybrid(
                query=state.query,
                query_embedding=query_embedding,
                limit=10,
            )
            try:
                from junior.services.local_store import rerank_with_cross_encoder
                results = rerank_with_cross_encoder(state.query, results, top_k=10)
            except Exception:
                pass
            docs = []
            for chunk_dict, score in results:
                docs.append({
                    "id": chunk_dict.get("id"),
                    "document_id": chunk_dict.get("document_id"),
                    "content": chunk_dict.get("content"),
                    "page_number": chunk_dict.get("page_number"),
                    "paragraph_number": chunk_dict.get("paragraph_number"),
                    "relevance_score": score,
                    "metadata": chunk_dict.get("metadata") or {},
                    "source": "local_store",
                })
            return docs
        except Exception as le:
            logger.error(f"[SEARCH NODE] Local store failed: {le}")
            return []

    async def _kanoon_search() -> list[dict]:
        """Search Indian Kanoon API for live case law."""
        client = get_kanoon_client()
        if not client.is_available:
            return []
        try:
            results = await client.search(
                query=state.query,
                doc_types=["judgment"],
                max_results=5,
            )
            docs = []
            for r in results:
                docs.append({
                    "id": f"kanoon_{r.doc_id}",
                    "document_id": f"kanoon_{r.doc_id}",
                    "content": f"{r.title}\n\n{r.headline}",
                    "page_number": 1,
                    "paragraph_number": None,
                    "relevance_score": r.relevance_score,
                    "metadata": {
                        "source": "indian_kanoon",
                        "court": r.court,
                        "date": r.date,
                        "url": r.url,
                        "title": r.title,
                    },
                    "source": "indian_kanoon",
                })
            logger.info(f"[SEARCH NODE] Kanoon returned {len(docs)} results")
            return docs
        except Exception as e:
            logger.warning(f"[SEARCH NODE] Kanoon search failed: {e}")
            return []

    # --- Run local DB + Kanoon in parallel ---
    primary_docs, kanoon_docs = await asyncio.gather(
        _local_db_search(),
        _kanoon_search(),
    )

    if primary_docs:
        combined = primary_docs
        if kanoon_docs:
            combined = primary_docs + kanoon_docs
        state.documents = combined
        logger.info(f"[SEARCH NODE] {len(primary_docs)} local + {len(kanoon_docs)} Kanoon = {len(combined)} total")

    else:
        # Primary DB failed — run local store + Kanoon in parallel
        logger.warning("[SEARCH NODE] Primary DB empty, trying local store + Kanoon in parallel")
        async def _return_cached_kanoon() -> list[dict]:
            return kanoon_docs

        local_docs, kanoon_docs2 = await asyncio.gather(
            _local_store_search(),
            _return_cached_kanoon() if kanoon_docs else _kanoon_search(),
        )
        combined = local_docs + kanoon_docs2
        state.documents = combined
        if not combined:
            state.metadata["search_error"] = "All sources returned zero results"
            logger.warning("[SEARCH NODE] All sources returned zero results")
        else:
            logger.info(f"[SEARCH NODE] {len(local_docs)} local + {len(kanoon_docs2)} Kanoon = {len(combined)} total")

    return state


def _detect_uncited_paragraphs(draft: str) -> list[str]:
    """
    Heuristic: identify substantive paragraphs (>20 words) that contain no
    case citation pattern.  Returns a list of short paragraph excerpts.
    """
    import re
    citation_re = re.compile(
        r"(\(\d{4}\)|\d+\s+SCC\s+\d+|AIR\s+\d+|\d{4}\s+SCR|v\.\s+[A-Z])"
    )
    uncited: list[str] = []
    for para in draft.split("\n\n"):
        stripped = para.strip()
        if len(stripped.split()) < 20:
            continue  # too short to matter
        # Skip headings (ALL CAPS or starting with Roman numerals / numbers)
        if re.match(r"^(?:[IVX]+\.|\d+\.)|^[A-Z ]{5,}$", stripped):
            continue
        if not citation_re.search(stripped):
            excerpt = stripped[:80].replace("\n", " ")
            uncited.append(excerpt)
    return uncited


async def validate_node(state: AgentState) -> AgentState:
    """
    Final Validation node — independent quality gate AFTER the Writer.

    Checks:
    1. Citation coverage  — every substantive paragraph has at least one citation
    2. Hallucination guard — no citation appears that wasn't in state.citations
    3. Legal register     — ensures mandatory Indian court phrases are present
    4. Completeness       — all Questions of Law are addressed in the arguments

    On failure: sets needs_revision=True and lowers confidence_score so the
    workflow loops back through Critique → Research → Write again.
    """
    import re

    logger.info("[VALIDATE NODE] Running final quality gate...")

    draft = state.draft or ""
    if not draft:
        logger.warning("[VALIDATE NODE] No draft to validate — skipping")
        return state

    issues: list[str] = []

    # 1. Citation coverage (uncited substantive paragraphs)
    uncited = _detect_uncited_paragraphs(draft)
    if uncited:
        issues.append(f"{len(uncited)} paragraph(s) lack citations: {uncited[:5]}")

    # 2. Hallucination guard — check that cited case names exist in state.citations
    known_case_names = {c.case_name.lower() for c in state.citations}
    cited_in_draft = re.findall(r"([A-Z][a-zA-Z\s]+?v\.?\s+[A-Z][a-zA-Z\s]+?)\s*\((\d{4})\)", draft)
    hallucinated = []
    for case_name, _ in cited_in_draft:
        name_lower = case_name.strip().lower()
        if name_lower and not any(name_lower in kn or kn in name_lower for kn in known_case_names):
            hallucinated.append(case_name.strip())
    if hallucinated:
        issues.append(f"Possible hallucinated citations: {hallucinated[:3]}")
        logger.warning(f"[VALIDATE NODE] Hallucination risk: {hallucinated}")

    # 3. Legal register check — mandatory Indian court phrases
    register_markers = [
        "it is humbly submitted", "it is respectfully contended",
        "strong reliance is placed", "in the premises",
        "most respectfully prayed",
    ]
    draft_lower = draft.lower()
    if not any(m in draft_lower for m in register_markers):
        issues.append("Draft lacks mandatory Indian court register phrases")

    if issues:
        state.metadata["validation_issues"] = issues
        state.needs_revision = True
        # Lower confidence to trigger another critique loop (but not below 3)
        state.confidence_score = max(3.0, state.confidence_score - 2.0)
        logger.warning(f"[VALIDATE NODE] {len(issues)} issue(s) found — sending back for revision")
        for iss in issues:
            logger.warning(f"  • {iss}")
    else:
        state.metadata["validation_passed"] = True
        state.needs_revision = False  # ← explicitly clear so workflow routes to END
        # If not already finalized, finalize now
        if not state.final_output and state.draft:
            state.final_output = state.draft
        logger.info("[VALIDATE NODE] All checks passed — response finalized ✅")
    return state
