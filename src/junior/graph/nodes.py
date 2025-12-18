"""
LangGraph workflow nodes for the Agentic RAG pipeline
"""

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

def _detect_uncited_paragraphs(text: str) -> list[int]:
    """Return 1-based indices of paragraphs that appear uncited.

    Heuristic: if a paragraph contains substantive content but no citation marker
    like 'Para', '(See:', 'SCC', 'AIR', etc., treat it as uncited.
    """
    import re

    if not text:
        return []

    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    markers = re.compile(r"\b(Para\s*\d+|at\s+Para\s*\d+|\(See:|SCC\b|AIR\b|CriLJ\b|supra\b)\b", re.IGNORECASE)

    uncited: list[int] = []
    for idx, p in enumerate(paras, 1):
        # Skip headings / very short lines
        if len(p) < 80:
            continue
        if not markers.search(p):
            uncited.append(idx)
    return uncited

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
    """
    from junior.db import DocumentRepository
    from junior.services.embedding import EmbeddingService

    logger.info("[SEARCH NODE] Searching for relevant documents...")

    query_embedding: Optional[list[float]] = None

    try:
        # Get embedding for the query
        embedding_service = EmbeddingService()
        query_embedding = await embedding_service.get_embedding(state.query)

        # Search the database
        doc_repo = DocumentRepository()
        results = await doc_repo.search_by_embedding(
            embedding=query_embedding,
            limit=10,
        )

        # Convert to dict format for state
        documents = []
        for chunk, score in results:
            documents.append({
                "id": chunk.id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "page_number": chunk.page_number,
                "paragraph_number": chunk.paragraph_number,
                "relevance_score": score,
                "metadata": chunk.metadata,
            })

        state.documents = documents
        logger.info(f"[SEARCH NODE] Found {len(documents)} relevant documents")

    except Exception as e:
        # Fallback: local on-disk store (dev mode / no Supabase)
        logger.warning(f"[SEARCH NODE] Primary search failed, trying local store: {e}")
        try:
            from pathlib import Path
            from junior.services.local_store import LocalDocumentStore

            store = LocalDocumentStore(Path("uploads"))
            local_results = store.search_hybrid(
                query=state.query,
                query_embedding=query_embedding,
                limit=10,
            )

            # Optional rerank (best-effort, requires sentence-transformers)
            try:
                from junior.services.local_store import rerank_with_cross_encoder
                local_results = rerank_with_cross_encoder(state.query, local_results, top_k=10)
            except Exception:
                pass

            documents = []
            for chunk_dict, score in local_results:
                documents.append({
                    "id": chunk_dict.get("id"),
                    "document_id": chunk_dict.get("document_id"),
                    "content": chunk_dict.get("content"),
                    "page_number": chunk_dict.get("page_number"),
                    "paragraph_number": chunk_dict.get("paragraph_number"),
                    "relevance_score": score,
                    "metadata": chunk_dict.get("metadata") or {},
                })
            state.documents = documents
            logger.info(f"[SEARCH NODE] Local store returned {len(documents)} chunks")
        except Exception as le:
            logger.error(f"[SEARCH NODE] Local store search failed: {le}")
            state.metadata["search_error"] = str(le)
            state.documents = []

    return state
