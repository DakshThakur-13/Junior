"""
LangGraph workflow for Legal Research
Implements the cyclic Agentic RAG pattern: Search → Research → Critique → Write → (loop or end)
"""

from typing import Any, Optional

from langgraph.graph import StateGraph, END

from junior.agents.base import AgentState
from junior.core import get_logger, settings
from junior.core.types import ResearchQuery, ResearchResult, Language
from .nodes import (
    research_node,
    critique_node,
    write_node,
    search_documents_node,
    validate_node,
    decide_next,
)

logger = get_logger(__name__)

def create_research_graph() -> Any:
    """
    Create the LangGraph workflow for legal research

    The workflow follows this pattern:

    ┌─────────────────────────────────────────────────────────────┐
    │                      START                                   │
    │                        │                                     │
    │                        ▼                                     │
    │                 ┌──────────────┐                            │
    │                 │   SEARCH     │  (parallel: DB + Kanoon)   │
    │                 │  Documents   │                            │
    │                 └──────────────┘                            │
    │                        │                                     │
    │                        ▼                                     │
    │                 ┌──────────────┐                            │
    │            ┌───▶│  RESEARCH    │◀───┐                       │
    │            │    │    Agent     │    │                       │
    │            │    └──────────────┘    │                       │
    │            │           │            │                       │
    │            │           ▼            │                       │
    │            │    ┌──────────────┐    │                       │
    │            │    │   CRITIQUE   │    │                       │
    │            │    │    Agent     │────┘                       │
    │            │    └──────────────┘  (if needs revision)       │
    │            │           │                                     │
    │            │           ▼                                     │
    │            │    ┌──────────────┐                            │
    │            │    │    WRITE     │                            │
    │            │    │    Agent     │                            │
    │            │    └──────────────┘                            │
    │            │           │                                     │
    │            │           ▼                                     │
    │            │    ┌──────────────┐                            │
    │            │    │   VALIDATE   │  (citation/hallucination)  │
    │            │    │    Gate      │                            │
    │            │    └──────────────┘                            │
    │            │       │         │                              │
    │            │  pass │         │ fail                        │
    │            │       ▼         └──────────────────────────┐  │
    │            │     END                                    │  │
    │            └───────────────────────────────────────────-┘  │
    │                  (loops back through critique)              │
    └─────────────────────────────────────────────────────────────┘

    Returns:
        Compiled StateGraph
    """

    # Create the graph with AgentState
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("search", search_documents_node)
    workflow.add_node("research", research_node)
    workflow.add_node("critique", critique_node)
    workflow.add_node("write", write_node)
    workflow.add_node("validate", validate_node)

    # Set entry point
    workflow.set_entry_point("search")

    # Fixed edges
    workflow.add_edge("search", "research")
    workflow.add_edge("research", "critique")
    workflow.add_edge("write", "validate")  # always validate after writing

    # critique → research (revision) or write (satisfied)
    workflow.add_conditional_edges(
        "critique",
        lambda state: "research" if state.needs_revision and state.iteration < state.max_iterations else "write",
        {
            "research": "research",
            "write": "write",
        },
    )

    # validate → END (pass) or critique (fail — trigger another loop)
    workflow.add_conditional_edges(
        "validate",
        lambda state: "end" if (
            not state.needs_revision
            or state.iteration >= state.max_iterations
        ) else "critique",
        {
            "end": END,
            "critique": "critique",
        },
    )

    return workflow.compile()

class LegalResearchWorkflow:
    """
    High-level wrapper for the legal research workflow

    Provides a simple interface for executing research queries
    and managing the workflow lifecycle.
    """

    def __init__(self, max_iterations: int = 3):
        self.max_iterations = max_iterations
        self._graph: Any = create_research_graph()
        self.logger = get_logger("workflow")

    async def research(
        self,
        query: str,
        language: Language = Language.ENGLISH,
        documents: Optional[list[dict]] = None,
    ) -> ResearchResult:
        """
        Execute a legal research query

        Args:
            query: The legal research question
            language: Preferred output language
            documents: Optional pre-loaded documents (bypasses search)

        Returns:
            ResearchResult with findings, citations, and final output
        """
        import time
        start_time = time.time()

        self.logger.info(f"Starting research: {query[:100]}...")

        # Initialize state
        initial_state = AgentState(
            query=query,
            language=language.value,
            documents=documents or [],
            max_iterations=self.max_iterations,
        )

        # Execute the workflow
        try:
            final_state = await self._graph.ainvoke(initial_state)
        except Exception as e:
            self.logger.error(f"Workflow error: {e}")
            raise

        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)

        summary = final_state.get("final_output") or final_state.get("draft")

        # Translate if needed (using AI4Bharat IndicTrans2)
        if language != Language.ENGLISH and summary:
            try:
                from junior.services import TranslationService
                translator = TranslationService()
                self.logger.info(f"Translating result to {language.value}...")

                # Use translate_response to preserve legal terms (Hinglish Bridge)
                translation_result = await translator.translate_response(
                    text=summary,
                    target_lang=language,
                    preserve_legal_terms=True
                )
                summary = translation_result.translated_text
            except Exception as e:
                self.logger.error(f"Translation failed: {e}")
                # Fallback: append a note or just return English
                summary += f"\n\n[Translation to {language.value} failed. Showing English original.]"

        # Build result
        result = ResearchResult(
            query=ResearchQuery(
                query=query,
                language=language,
            ),
            results=[],  # Would populate from search results
            summary=summary,
            total_found=len(final_state.get("documents", [])),
            processing_time_ms=processing_time,
        )

        self.logger.info(
            f"Research complete. Time: {processing_time}ms, "
            f"Citations: {len(final_state.get('citations', []))}"
        )

        return result

    async def research_with_trace(
        self,
        query: str,
        language: Language = Language.ENGLISH,
    ) -> tuple[ResearchResult, list[dict], dict]:
        """
        Execute research with full trace of agent reasoning

        Used for the "Show Logic" UI feature

        Args:
            query: The legal research question
            language: Preferred output language

        Returns:
            Tuple of (ResearchResult, trace_logs)
        """
        import time

        trace_logs = []
        start_time = time.time()
        latest_state: dict = {}

        # Initialize state
        initial_state = AgentState(
            query=query,
            language=language.value,
            max_iterations=self.max_iterations,
        )

        # Execute with streaming to capture intermediate states
        async for event in self._graph.astream(initial_state):
            node_name = list(event.keys())[0]
            node_state = event[node_name]

            if isinstance(node_state, dict):
                latest_state = node_state

            trace_logs.append({
                "node": node_name,
                "timestamp": time.time() - start_time,
                "iteration": node_state.get("iteration", 0),
                "citations_count": len(node_state.get("citations", [])),
                "confidence": node_state.get("confidence_score", 0),
                "needs_revision": node_state.get("needs_revision", False),
            })

        final_output = latest_state.get("final_output") or latest_state.get("draft")

        # Translate if needed
        if language != Language.ENGLISH and final_output:
            try:
                from junior.services import TranslationService
                translator = TranslationService()
                translation_result = await translator.translate_response(
                    text=final_output,
                    target_lang=language,
                    preserve_legal_terms=True
                )
                final_output = translation_result.translated_text
            except Exception as e:
                # Log but don't fail the trace
                pass

        result = ResearchResult(
            query=ResearchQuery(query=query, language=language),
            summary=final_output,
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

        return result, trace_logs, latest_state

# Convenience function for quick research
async def quick_research(query: str) -> str:
    """
    Quick research function for simple queries

    Args:
        query: Legal research question

    Returns:
        Final output text
    """
    workflow = LegalResearchWorkflow(max_iterations=2)
    result = await workflow.research(query)
    return result.summary or "No results found."
