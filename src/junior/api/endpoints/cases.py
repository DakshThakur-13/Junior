from __future__ import annotations

"""Case History and Timeline API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime
from enum import Enum
from uuid import uuid4

def _try_build_cases_from_local_store() -> list[CaseHistory]:
    """Best-effort case list from locally stored documents.

    This avoids serving hardcoded mock/demo cases. If there are no uploaded
    case documents, returns an empty list.
    """
    try:
        from pathlib import Path
        import json
        from collections import defaultdict
        from datetime import date as date_type, datetime as dt_type

        docs_dir = Path("uploads") / "documents"
        if not docs_dir.exists():
            return []

        grouped: dict[str, list[dict]] = defaultdict(list)
        for fp in docs_dir.glob("*.json"):
            try:
                doc = json.loads(fp.read_text(encoding="utf-8"))
                if not isinstance(doc, dict):
                    continue
                case_number = str(doc.get("case_number") or "").strip()
                if not case_number or case_number.upper() == "MANUAL":
                    continue
                grouped[case_number].append(doc)
            except Exception:
                continue

        cases: list[CaseHistory] = []
        for case_number, docs in grouped.items():
            # Determine filing_date as earliest document date
            filing = None
            for d in docs:
                raw = d.get("date")
                if not raw:
                    continue
                try:
                    if isinstance(raw, str):
                        # Accept ISO date or datetime
                        if "T" in raw:
                            dt = dt_type.fromisoformat(raw.replace("Z", "+00:00"))
                            val = dt.date()
                        else:
                            val = dt_type.fromisoformat(raw).date()
                    else:
                        val = None
                    if isinstance(val, date_type):
                        filing = val if filing is None or val < filing else filing
                except Exception:
                    continue

            filing_date = filing or date.today()
            first = docs[0]

            cases.append(
                CaseHistory(
                    id=case_number,
                    case_number=case_number,
                    title=str(first.get("title") or case_number),
                    court=str(first.get("court") or ""),
                    bench=None,
                    status=CaseStatus.PENDING,
                    filing_date=filing_date,
                    next_hearing=None,
                    parties=[],
                    subject_matter=[],
                    acts_sections=[],
                    timeline=[],
                    related_cases=[],
                    notes=None,
                )
            )

        return cases
    except Exception:
        return []

router = APIRouter()

class CaseStatus(str, Enum):
    PENDING = "pending"
    DISPOSED = "disposed"
    RESERVED = "reserved"
    LISTED = "listed"
    ADJOURNED = "adjourned"

class EventType(str, Enum):
    FILING = "filing"
    HEARING = "hearing"
    ORDER = "order"
    EVIDENCE = "evidence"
    ARGUMENT = "argument"
    JUDGMENT = "judgment"
    APPEAL = "appeal"
    OTHER = "other"

class CaseParty(BaseModel):
    name: str
    role: str  # petitioner, respondent, intervenor, etc.
    advocate: Optional[str] = None

class TimelineEvent(BaseModel):
    id: str
    date: date
    event_type: EventType
    title: str
    description: Optional[str] = None
    documents: List[str] = []
    order_link: Optional[str] = None

class CaseHistory(BaseModel):
    id: str
    case_number: str
    title: str
    court: str
    bench: Optional[str] = None
    status: CaseStatus
    filing_date: date
    next_hearing: Optional[date] = None
    parties: List[CaseParty]
    subject_matter: List[str]
    acts_sections: List[str]
    timeline: List[TimelineEvent]
    related_cases: List[str] = []
    notes: Optional[str] = None

class CaseSearchRequest(BaseModel):
    query: Optional[str] = None
    court: Optional[str] = None
    status: Optional[CaseStatus] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    party_name: Optional[str] = None
    advocate: Optional[str] = None

class CaseListResponse(BaseModel):
    cases: List[CaseHistory]
    total: int
    page: int
    page_size: int

@router.get("/", response_model=CaseListResponse)
async def list_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    court: Optional[str] = None,
    status: Optional[CaseStatus] = None,
    search: Optional[str] = None,
):
    """
    List cases with filtering and pagination.
    """
    filtered = _try_build_cases_from_local_store()

    if court:
        filtered = [c for c in filtered if court.lower() in c.court.lower()]

    if status:
        filtered = [c for c in filtered if c.status == status]

    if search:
        search_lower = search.lower()
        filtered = [c for c in filtered if
                    search_lower in c.title.lower() or
                    search_lower in c.case_number.lower()]

    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size

    return CaseListResponse(
        cases=filtered[start:end],
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/{case_id}", response_model=CaseHistory)
async def get_case(case_id: str):
    """
    Get detailed case history by ID.
    """
    for case in _try_build_cases_from_local_store():
        if case.id == case_id:
            return case

    raise HTTPException(status_code=404, detail="Case not found")

@router.post("/search", response_model=CaseListResponse)
async def search_cases(request: CaseSearchRequest):
    """
    Advanced search for cases.
    """
    filtered = _try_build_cases_from_local_store()

    if request.court:
        filtered = [c for c in filtered if request.court.lower() in c.court.lower()]

    if request.status:
        filtered = [c for c in filtered if c.status == request.status]

    if request.from_date:
        filtered = [c for c in filtered if c.filing_date >= request.from_date]

    if request.to_date:
        filtered = [c for c in filtered if c.filing_date <= request.to_date]

    if request.party_name:
        name_lower = request.party_name.lower()
        filtered = [c for c in filtered if
                    any(name_lower in p.name.lower() for p in c.parties)]

    if request.advocate:
        adv_lower = request.advocate.lower()
        filtered = [c for c in filtered if
                    any(p.advocate and adv_lower in p.advocate.lower() for p in c.parties)]

    if request.query:
        query_lower = request.query.lower()
        filtered = [c for c in filtered if
                    query_lower in c.title.lower() or
                    query_lower in c.case_number.lower() or
                    any(query_lower in s.lower() for s in c.subject_matter)]

    return CaseListResponse(
        cases=filtered,
        total=len(filtered),
        page=1,
        page_size=len(filtered)
    )

@router.get("/{case_id}/timeline", response_model=List[TimelineEvent])
async def get_case_timeline(case_id: str):
    """
    Get timeline events for a case.
    """
    for case in _try_build_cases_from_local_store():
        if case.id == case_id:
            # Local-derived cases don't yet persist timeline events.
            return []

    raise HTTPException(status_code=404, detail="Case not found")

@router.post("/{case_id}/timeline")
async def add_timeline_event(case_id: str, event: TimelineEvent):
    """
    Add a new timeline event to a case.
    """
    # Not persisted yet (requires DB table + auth).
    raise HTTPException(
        status_code=501,
        detail="Case timeline persistence is not configured (no backing store).",
    )

@router.get("/{case_id}/related")
async def get_related_cases(case_id: str):
    """
    Get cases related to a specific case.
    """
    for case in _try_build_cases_from_local_store():
        if case.id == case_id:
            return {"case_id": case_id, "related_cases": []}

    raise HTTPException(status_code=404, detail="Case not found")

@router.get("/upcoming-hearings/")
async def get_upcoming_hearings(
    days: int = Query(30, ge=1, le=90),
):
    """
    Get cases with upcoming hearings within specified days.
    """
    from datetime import timedelta

    today = date.today()
    end_date = today + timedelta(days=days)

    # Local-derived cases don't have hearing dates yet.
    upcoming = []

    upcoming.sort(key=lambda x: x["hearing_date"])

    return {
        "from_date": today,
        "to_date": end_date,
        "hearings": upcoming
    }
