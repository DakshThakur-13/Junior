"""
Type definitions and enums for Junior
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

class CaseStatus(str, Enum):
    """Status of a case law citation"""
    GOOD_LAW = "good_law"  # 🟢 Safe to cite
    DISTINGUISHED = "distinguished"  # 🟡 Use with caution
    OVERRULED = "overruled"  # 🔴 Do not use

class Court(str, Enum):
    """Indian Court hierarchy"""
    SUPREME_COURT = "supreme_court"
    HIGH_COURT = "high_court"
    DISTRICT_COURT = "district_court"
    TRIBUNAL = "tribunal"
    OTHER = "other"

class Language(str, Enum):
    """Supported languages"""
    ENGLISH = "en"
    HINDI = "hi"
    MARATHI = "mr"
    TAMIL = "ta"
    TELUGU = "te"
    BENGALI = "bn"
    GUJARATI = "gu"
    KANNADA = "kn"
    MALAYALAM = "ml"
    PUNJABI = "pa"

class AgentRole(str, Enum):
    """Roles for AI Agents in the workflow"""
    RESEARCHER = "researcher"
    CRITIC = "critic"
    WRITER = "writer"
    TRANSLATOR = "translator"

# ============ Base Models ============

class Citation(BaseModel):
    """A legal citation with pinpoint reference"""
    case_name: str
    case_number: str
    court: Court
    year: int
    paragraph: Optional[int] = None
    page: Optional[int] = None
    status: CaseStatus = CaseStatus.GOOD_LAW
    source_document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    excerpt: Optional[str] = None

    @property
    def formatted(self) -> str:
        """Get formatted citation string"""
        base = f"{self.case_name} ({self.year}) {self.court.value.replace('_', ' ').title()}"
        if self.paragraph:
            base += f" at Para {self.paragraph}"
        return base

class DocumentChunk(BaseModel):
    """A chunk of a legal document with metadata"""
    id: str
    document_id: str
    content: str
    page_number: int
    paragraph_number: Optional[int] = None
    embedding: Optional[list[float]] = None
    metadata: dict = Field(default_factory=dict)

class LegalDocument(BaseModel):
    """A legal document (judgment, brief, etc.)"""
    id: str
    title: str
    court: Court
    case_number: str
    date: datetime
    judges: list[str] = Field(default_factory=list)
    parties: dict = Field(default_factory=dict)
    summary: Optional[str] = None
    full_text: Optional[str] = None
    chunks: list[DocumentChunk] = Field(default_factory=list)
    status: CaseStatus = CaseStatus.GOOD_LAW
    language: Language = Language.ENGLISH
    metadata: dict = Field(default_factory=dict)

class SearchResult(BaseModel):
    """A search result from the RAG pipeline"""
    document: LegalDocument
    chunk: DocumentChunk
    relevance_score: float
    citation: Citation
    highlight: Optional[str] = None

class AgentMessage(BaseModel):
    """A message from an AI agent"""
    role: AgentRole
    content: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = 0.0
    reasoning: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ResearchQuery(BaseModel):
    """A legal research query"""
    query: str
    language: Language = Language.ENGLISH
    court_filter: Optional[list[Court]] = None
    year_range: Optional[tuple[int, int]] = None
    include_overruled: bool = False
    max_results: int = 10

class ResearchResult(BaseModel):
    """Result of a legal research query"""
    query: ResearchQuery
    results: list[SearchResult] = Field(default_factory=list)
    summary: Optional[str] = None
    agent_messages: list[AgentMessage] = Field(default_factory=list)
    total_found: int = 0
    processing_time_ms: int = 0
