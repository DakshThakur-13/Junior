"""
API Request/Response Schemas
"""

from datetime import datetime
from typing import Optional
from typing import Literal
from pydantic import BaseModel, Field

from junior.core.types import Language, Court, CaseStatus

# ============ Research Schemas ============

class CitationResponse(BaseModel):
    """Citation in API response"""
    case_name: str
    case_number: str
    court: str
    year: int
    paragraph: Optional[int] = None
    status: str
    status_emoji: str
    formatted: str

    class Config:
        from_attributes = True

class ResearchRequest(BaseModel):
    """Request for legal research"""
    query: str = Field(..., min_length=10, max_length=5000, description="Legal research query")
    language: Language = Field(default=Language.ENGLISH, description="Preferred output language")
    court_filter: Optional[list[Court]] = Field(default=None, description="Filter by court type")
    include_overruled: bool = Field(default=False, description="Include overruled cases")
    max_iterations: int = Field(default=3, ge=1, le=5, description="Max research iterations")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What are the grounds for anticipatory bail under Section 438 CrPC?",
                "language": "en",
                "max_iterations": 3,
            }
        }

class ResearchResponse(BaseModel):
    """Response from legal research"""
    query: str
    summary: str
    citations: list[CitationResponse]
    confidence_score: float
    confidence_band: str = "low"
    iterations: int
    processing_time_ms: int
    evidence_sufficiency: str = "insufficient"
    verified_citation_count: int = 0
    total_citation_count: int = 0
    ai_disclaimer: str = "AI-assisted output. Verify with official records before filing."
    trace: Optional[list[dict]] = None  # For "Show Logic" feature

    class Config:
        from_attributes = True

# ============ Document Schemas ============

class DocumentUploadRequest(BaseModel):
    """Request for document upload metadata"""
    title: Optional[str] = None
    court: Optional[Court] = None
    case_number: Optional[str] = None

class DocumentUploadResponse(BaseModel):
    """Response after document upload"""
    document_id: str
    title: str
    court: str
    pages: int
    chunks: int
    status: str = "processed"

class DocumentSearchRequest(BaseModel):
    """Request for document search"""
    query: str
    limit: int = Field(default=10, ge=1, le=50)
    court_filter: Optional[list[Court]] = None
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)

class DocumentSearchResult(BaseModel):
    """Single search result"""
    document_id: str
    title: str
    content: str
    page_number: int
    paragraph_number: Optional[int]
    relevance_score: float
    citation: Optional[CitationResponse]

# ============ Chat Schemas ============

class ChatMessage(BaseModel):
    """A chat message"""
    id: str
    role: str  # user, assistant, system
    content: str
    citations: list[CitationResponse] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatSession(BaseModel):
    """A chat session"""
    id: str
    title: str
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

class ChatRequest(BaseModel):
    """Request to send a chat message"""
    session_id: Optional[str] = None  # None to create new session
    message: str = Field(..., min_length=1, max_length=5000)
    language: Language = Language.ENGLISH
    input_language: Optional[Language] = Field(
        default=None,
        description="Optional hint for the language of `message` (useful for Roman-script Hindi/Marathi).",
    )
    output_script: Optional[Literal["native", "roman"]] = Field(
        default=None,
        description="Optional output script preference for Indic languages (native script or Romanized).",
    )
    use_research: Optional[bool] = Field(
        default=None,
        description="Optional explicit switch for deeper legal research mode.",
    )
    suggest_actions: bool = Field(
        default=True,
        description="Whether the assistant should suggest practical next actions.",
    )
    protocol_id: Optional[str] = Field(default=None, description="Optional lawyer protocol id (e.g., criminal_anticipatory_bail_438)")

class ChatResponse(BaseModel):
    """Response from chat"""
    session_id: str
    message: ChatMessage
    related_documents: list[DocumentSearchResult] = Field(default_factory=list)

# ============ Translation Schemas ============

class TranslateRequest(BaseModel):
    """Request for translation"""
    text: str = Field(..., min_length=1, max_length=10000)
    target_language: Language
    preserve_legal_terms: bool = True

class TranslateResponse(BaseModel):
    """Response from translation"""
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    preserved_terms: list[str]

# ============ Formatting Schemas ============

class FormatDocumentRequest(BaseModel):
    """Request to format a document"""
    content: str = Field(..., min_length=1)
    document_type: str = Field(..., description="Type: writ_petition, written_statement, etc.")
    court: Court
    case_number: str
    petitioner: str = "Petitioner"
    respondent: str = "Respondent"

class FormatDocumentResponse(BaseModel):
    """Response with formatted document"""
    formatted_text: str
    html: str
    court: str
    document_type: str

# ============ Analysis Schemas ============

class JudgeAnalyticsRequest(BaseModel):
    """Request for judge analytics"""
    judge_name: str
    court: Optional[Court] = None
    case_type: Optional[str] = None
    judgments: list[str] = Field(default_factory=list, description="Optional judgment excerpts to analyze. If empty, AI will auto-fetch.")
    case_details: Optional[str] = Field(default=None, description="Description of user's case/application situation")
    time_period: Optional[str] = Field(default=None, description="Time period for fetching judgments (e.g., '2022-2024')")
    cases_count: Optional[int] = Field(default=15, description="Number of cases to analyze (1-100)")

class JudgeAnalyticsResponse(BaseModel):
    """Response with judge analytics"""
    judge_name: str
    total_cases_analyzed: int
    patterns: list[dict]
    recommendations: list[str]
    source_provenance: list[dict] = Field(default_factory=list)

class DevilsAdvocateRequest(BaseModel):
    """Request for Devil's Advocate simulation"""
    case_summary: str
    arguments: str
    citations: list[str] = Field(default_factory=list)
    protocol_id: Optional[str] = Field(default=None, description="Optional lawyer protocol id")

class DevilsAdvocateResponse(BaseModel):
    """Response from Devil's Advocate"""
    attack_points: list[dict]
    vulnerability_score: float
    preparation_recommendations: list[str]
    confidence_band: str = "low"
    evidence_sufficiency: str = "insufficient"
    ai_disclaimer: str = "AI-assisted adversarial analysis. Not a substitute for advocate judgment."

# ============ Official Sources Schemas ============

class OfficialSourceItem(BaseModel):
    """A curated source entry shown in Research tab."""
    id: str
    title: str
    type: str  # Official | Study | Act | Constitution | Precedent | Law | Web
    summary: str
    source: str
    url: str
    publisher: str
    authority: str  # official | study | web
    tags: list[str] = Field(default_factory=list)
    score: float = 0.0

class OfficialSourcesSearchRequest(BaseModel):
    """Search curated official sources and study material."""
    query: str = Field(default="", max_length=500)
    category: Optional[str] = Field(default=None, description="Filter by type: Official, Study, Act, etc")
    authority: Optional[str] = Field(default=None, description="Filter by authority: official or study")
    limit: int = Field(default=50, ge=1, le=200)

class OfficialSourcesSearchResponse(BaseModel):
    query: str
    results: list[OfficialSourceItem]
    total_count: int = 0
    search_time_ms: int = 0

class ManualIngestRequest(BaseModel):
    """Request to ingest a public manual/book into the local RAG store."""
    source_id: str = Field(..., min_length=1, description="Catalog source id to ingest")
    force: bool = Field(default=False, description="Re-download and re-index even if already ingested")

class ManualIngestResponse(BaseModel):
    source_id: str
    document_id: str
    title: str
    chunks: int
    bytes_downloaded: int
    source_url: str
    status: str

# ============ Lawyer Protocol Schemas ============

class LawyerProtocolItem(BaseModel):
    id: str
    title: str
    domain: str
    purpose: str

class LawyerProtocolsResponse(BaseModel):
    protocols: list[LawyerProtocolItem]

# ============ Detective Wall Schemas ============

class DetectiveWallNode(BaseModel):
    """A node on the detective wall canvas"""
    id: str
    title: str
    type: str  # Evidence | Precedent | Statement | Strategy | etc.
    status: Optional[str] = None  # Verified | Contested | etc.
    date: Optional[str] = None
    content: Optional[str] = None

class DetectiveWallEdge(BaseModel):
    """A relationship between two nodes"""
    source: str
    target: str
    label: str

class DetectiveWallInsight(BaseModel):
    title: str
    detail: str
    severity: str  # low | medium | high
    node_ids: list[str] = Field(default_factory=list)

class DetectiveWallSuggestedLink(BaseModel):
    source: str
    target: str
    label: str
    confidence: float = 0.0
    reason: Optional[str] = None

class DetectiveWallAnalyzeRequest(BaseModel):
    case_context: Optional[str] = None
    nodes: list[DetectiveWallNode]
    edges: list[DetectiveWallEdge] = Field(default_factory=list)

class DetectiveWallAnalyzeResponse(BaseModel):
    summary: str
    insights: list[DetectiveWallInsight] = Field(default_factory=list)
    suggested_links: list[DetectiveWallSuggestedLink] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)

# ============ Health Check ============

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: Optional[str] = None
    environment: str = "development"
    services: dict[str, str] = Field(default_factory=dict)
