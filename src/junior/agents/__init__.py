"""
AI Agents for Junior Legal Assistant
Implements the Agentic RAG workflow with Researcher, Critic, and Writer agents
"""

from .base import BaseAgent
from .researcher import ResearcherAgent
from .critic import CriticAgent
from .writer import WriterAgent
from .detective_wall import DetectiveWallAgent
from .judge_analytics import JudgeAnalyticsAgent

__all__ = [
    "BaseAgent",
    "ResearcherAgent",
    "CriticAgent",
    "WriterAgent",
    "DetectiveWallAgent",
    "JudgeAnalyticsAgent",
]
