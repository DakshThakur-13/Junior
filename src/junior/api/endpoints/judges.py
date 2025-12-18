"""Judge Profiles API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from enum import Enum

from junior.agents.judge_analytics import JudgeAnalyticsAgent
from junior.api.schemas import JudgeAnalyticsRequest, JudgeAnalyticsResponse
from junior.core.exceptions import LLMNotConfiguredError

router = APIRouter()

class CourtType(str, Enum):
    SUPREME_COURT = "supreme_court"
    HIGH_COURT = "high_court"
    TRIBUNAL = "tribunal"
    DISTRICT_COURT = "district_court"

class JudgeStatus(str, Enum):
    SITTING = "sitting"
    RETIRED = "retired"

class CareerEntry(BaseModel):
    year: int
    position: str
    court: str

class NotableJudgment(BaseModel):
    title: str
    citation: str
    summary: str
    year: Optional[int] = None

class JudgeTendencies(BaseModel):
    bail_grant_rate: float
    conviction_rate: float
    injunction_rate: float
    settlement_preference: float
    avg_disposal_days: int

class JudgeProfile(BaseModel):
    id: str
    name: str
    honorific: str = "Hon'ble Justice"
    court: str
    court_type: CourtType
    status: JudgeStatus
    specializations: List[str]
    total_judgments: int
    tendencies: JudgeTendencies
    judicial_philosophy: str
    litigation_tips: List[str]
    notable_judgments: List[NotableJudgment]
    career: List[CareerEntry]

class JudgeListResponse(BaseModel):
    judges: List[JudgeProfile]
    total: int
    page: int
    page_size: int

class JudgeSearchRequest(BaseModel):
    query: Optional[str] = None
    courts: Optional[List[CourtType]] = None
    specializations: Optional[List[str]] = None
    status: Optional[JudgeStatus] = None

@router.get("/", response_model=JudgeListResponse)
async def list_judges(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    court_type: Optional[CourtType] = None,
    status: Optional[JudgeStatus] = None,
    specialization: Optional[str] = None,
    search: Optional[str] = None,
):
    """
    List judges with filtering and pagination.
    """
    # No hardcoded/demo judge data. Populate via your own corpus/DB.
    filtered: list[JudgeProfile] = []

    if court_type:
        filtered = [j for j in filtered if j.court_type == court_type]

    if status:
        filtered = [j for j in filtered if j.status == status]

    if specialization:
        filtered = [j for j in filtered if specialization in j.specializations]

    if search:
        search_lower = search.lower()
        filtered = [j for j in filtered if search_lower in j.name.lower()]

    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size

    return JudgeListResponse(
        judges=filtered[start:end],
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/{judge_id}", response_model=JudgeProfile)
async def get_judge(judge_id: str):
    """
    Get detailed judge profile by ID.
    """
    raise HTTPException(status_code=404, detail="Judge not found")

@router.post("/search", response_model=JudgeListResponse)
async def search_judges(request: JudgeSearchRequest):
    """
    Advanced search for judges.
    """
    filtered: list[JudgeProfile] = []

    if request.courts:
        filtered = [j for j in filtered if j.court_type in request.courts]

    if request.specializations:
        filtered = [j for j in filtered if any(s in j.specializations for s in request.specializations)]

    if request.status:
        filtered = [j for j in filtered if j.status == request.status]

    if request.query:
        query_lower = request.query.lower()
        filtered = [j for j in filtered if query_lower in j.name.lower() or
                    query_lower in j.judicial_philosophy.lower()]

    return JudgeListResponse(
        judges=filtered,
        total=len(filtered),
        page=1,
        page_size=len(filtered)
    )

@router.get("/{judge_id}/judgments")
async def get_judge_judgments(
    judge_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
):
    """
    Get list of judgments by a specific judge.
    """
    # Requires a backing corpus; not served as mock data.
    raise HTTPException(status_code=404, detail="Judge not found")

@router.get("/{judge_id}/tendencies")
async def get_judge_tendencies(judge_id: str):
    """
    Get AI-analyzed judicial tendencies for a judge.
    """
    # Requires a backing corpus; not served as mock data.
    raise HTTPException(status_code=404, detail="Judge not found")

@router.post("/analyze", response_model=JudgeAnalyticsResponse)
async def analyze_judge(request: JudgeAnalyticsRequest):
    """Analyze a judge from provided judgment excerpts.

    This endpoint is intentionally input-driven so it works without a configured
    Supabase corpus. Provide `judgments` (excerpts) and Junior will extract
    patterns + litigation recommendations.
    """
    if not request.judgments:
        raise HTTPException(
            status_code=400,
            detail="No judgment excerpts provided. Pass `judgments` (list of text snippets) to analyze.",
        )

    agent = JudgeAnalyticsAgent()
    try:
        result = await agent.analyze(
            judge_name=request.judge_name,
            court=request.court.value if request.court else None,
            case_type=request.case_type,
            judgments=request.judgments,
        )
        return JudgeAnalyticsResponse(**result)
    except LLMNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e))
