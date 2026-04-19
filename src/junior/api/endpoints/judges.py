"""Judge Profiles API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from enum import Enum

from junior.agents.judge_analytics import JudgeAnalyticsAgent
from junior.api.schemas import JudgeAnalyticsRequest, JudgeAnalyticsResponse
from junior.core.exceptions import LLMNotConfiguredError
from junior.services.judge_corpus import get_judge_corpus_service

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
    service = get_judge_corpus_service()
    filtered, total = await service.list_profiles(
        page=page,
        page_size=page_size,
        court_type=court_type.value if court_type else None,
        status=status.value if status else None,
        specialization=specialization,
        search=search,
    )

    return JudgeListResponse(
        judges=filtered,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{judge_id}", response_model=JudgeProfile)
async def get_judge(judge_id: str):
    """
    Get detailed judge profile by ID.
    """
    service = get_judge_corpus_service()
    profile = await service.get_profile(judge_id)
    if profile:
        return JudgeProfile(**profile)
    raise HTTPException(status_code=404, detail="Judge not found")


@router.post("/search", response_model=JudgeListResponse)
async def search_judges(request: JudgeSearchRequest):
    """
    Advanced search for judges.
    """
    service = get_judge_corpus_service()
    filtered, total = await service.list_profiles(
        page=1,
        page_size=500,
        court_type=request.courts[0].value if request.courts else None,
        status=request.status.value if request.status else None,
        specialization=request.specializations[0] if request.specializations else None,
        search=request.query,
    )

    return JudgeListResponse(
        judges=filtered,
        total=total,
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
    service = get_judge_corpus_service()
    judgments = await service.get_judgments(judge_name=judge_id, limit=page_size)
    if not judgments:
        raise HTTPException(status_code=404, detail="Judge not found")
    return {
        "judge_id": judge_id,
        "page": page,
        "page_size": page_size,
        "total": len(judgments),
        "judgments": judgments,
    }


@router.get("/{judge_id}/tendencies")
async def get_judge_tendencies(judge_id: str):
    """
    Get AI-analyzed judicial tendencies for a judge.
    """
    service = get_judge_corpus_service()
    profile = await service.get_profile(judge_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Judge not found")
    return profile.get("tendencies", {})


@router.post("/analyze", response_model=JudgeAnalyticsResponse)
async def analyze_judge(request: JudgeAnalyticsRequest):
    """Analyze a judge from provided judgment excerpts or auto-fetch them.

    If `judgments` is empty, the AI will automatically search for and fetch
    the judge's past judgments based on the provided case type and analyze them.
    """
    service = get_judge_corpus_service()
    judgments = list(request.judgments)
    source_provenance: list[dict] = []
    if not judgments:
        records, source_provenance = await service.get_judgments_with_provenance(
            judge_name=request.judge_name,
            court=request.court.value if request.court else None,
            case_type=request.case_type,
            limit=request.cases_count or 15,
        )

        judgments = []
        for item in records:
            parts = [
                f"Title: {item.get('title') or 'Untitled Judgment'}",
                f"Citation: {item.get('citation') or item.get('case_number') or 'Unknown'}",
            ]
            if item.get("year"):
                parts.append(f"Year: {item.get('year')}")
            if item.get("court"):
                parts.append(f"Court: {item.get('court')}")
            if item.get("case_type"):
                parts.append(f"Case Type: {item.get('case_type')}")
            if item.get("legal_status"):
                parts.append(f"Outcome: {item.get('legal_status')}")
            if item.get("summary"):
                parts.append(f"Summary: {item.get('summary')}")
            if item.get("source_url"):
                parts.append(f"Source: {item.get('source_url')}")
            judgments.append("\n".join(parts))

    if not judgments:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No judgment corpus was found for {request.judge_name}. "
                f"Try a different name or import more judgments into Supabase."
            ),
        )

    agent = JudgeAnalyticsAgent()
    try:
        result = await agent.analyze(
            judge_name=request.judge_name,
            court=request.court.value if request.court else None,
            case_type=request.case_type,
            judgments=judgments,
        )
        return JudgeAnalyticsResponse(**result, source_provenance=source_provenance)
    except LLMNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e))
