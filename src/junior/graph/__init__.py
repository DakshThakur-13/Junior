"""
LangGraph workflow definitions for Junior
Implements the Agentic RAG pipeline
"""

from .workflow import LegalResearchWorkflow, create_research_graph
from .nodes import research_node, critique_node, write_node, decide_next

__all__ = [
    "LegalResearchWorkflow",
    "create_research_graph",
    "research_node",
    "critique_node",
    "write_node",
    "decide_next",
]
