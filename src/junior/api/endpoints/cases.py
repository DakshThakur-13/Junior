from __future__ import annotations

"""Case History and Timeline API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime
from enum import Enum
import hashlib
import json
from pathlib import Path

from junior.services.audit_log import AuditEvent, append_audit_event


_DEMO_DOCUMENT_ID_PREFIXES = (
    "650e8400-e29b-41d4-a716-44665544",
)


def _safe_date(raw: object) -> Optional[date]:
    if not raw:
        return None
    try:
        if isinstance(raw, str):
            value = raw.replace("Z", "+00:00")
            return datetime.fromisoformat(value).date()
        if isinstance(raw, datetime):
            return raw.date()
        if isinstance(raw, date):
            return raw
    except Exception:
        return None
    return None


def _as_case_status(raw: object) -> "CaseStatus":
    text = str(raw or "").strip().lower()
    if text in {"good_law", "distinguished", "overruled", "historical_record"}:
        return CaseStatus.DISPOSED
    if text in {"disposed", "decided", "closed"}:
        return CaseStatus.DISPOSED
    if text in {"reserved", "judgment_reserved"}:
        return CaseStatus.RESERVED
    if text in {"listed", "listed_for_hearing"}:
        return CaseStatus.LISTED
    if text in {"adjourned", "part_heard"}:
        return CaseStatus.ADJOURNED
    return CaseStatus.PENDING


def _build_parties(party_map: object) -> list["CaseParty"]:
    if not isinstance(party_map, dict):
        return []

    parties: list[CaseParty] = []
    role_aliases = {
        "petitioner": "petitioner",
        "respondent": "respondent",
        "plaintiff": "petitioner",
        "defendant": "respondent",
        "complainant": "petitioner",
        "accused": "respondent",
        "appellant": "petitioner",
    }

    for key, val in party_map.items():
        role = role_aliases.get(str(key).lower(), str(key).lower())
        if isinstance(val, str) and val.strip():
            parties.append(CaseParty(name=val.strip(), role=role))
        elif isinstance(val, list):
            for v in val:
                if isinstance(v, str) and v.strip():
                    parties.append(CaseParty(name=v.strip(), role=role))

    return parties


def _normalize_court(raw: object) -> str:
    text = str(raw or "").strip()
    if not text:
        return "other"
    return text.lower()


def _is_demo_seed_document_id(raw_id: object) -> bool:
    value = str(raw_id or "").strip().lower()
    if not value:
        return False
    return any(value.startswith(prefix) for prefix in _DEMO_DOCUMENT_ID_PREFIXES)


def _build_cases_from_grouped_docs(grouped: dict[str, list[dict]]) -> list["CaseHistory"]:
    from datetime import date as date_type

    cases: list[CaseHistory] = []
    for case_number, docs in grouped.items():
        docs_sorted = sorted(
            docs,
            key=lambda d: _safe_date(d.get("date")) or date_type.min,
        )
        first = docs_sorted[0]
        latest = docs_sorted[-1]

        doc_dates = [_safe_date(d.get("date")) for d in docs_sorted]
        doc_dates = [d for d in doc_dates if d is not None]
        filing_date = min(doc_dates) if doc_dates else date.today()

        metadata_latest = latest.get("metadata") if isinstance(latest.get("metadata"), dict) else {}
        next_hearing = _safe_date(metadata_latest.get("next_hearing"))
        parties = _build_parties(latest.get("parties"))

        subject_matter = metadata_latest.get("subject_matter")
        if not isinstance(subject_matter, list):
            subject_matter = []
        if not subject_matter:
            subject_matter = latest.get("keywords") if isinstance(latest.get("keywords"), list) else []

        acts_sections = metadata_latest.get("acts_sections")
        if not isinstance(acts_sections, list):
            acts_sections = []
        if not acts_sections:
            acts_sections = latest.get("legal_provisions") if isinstance(latest.get("legal_provisions"), list) else []

        related_cases = metadata_latest.get("related_cases")
        if not isinstance(related_cases, list):
            related_cases = []

        timeline: list[TimelineEvent] = []
        for idx, d in enumerate(docs_sorted, 1):
            dmeta = d.get("metadata") if isinstance(d.get("metadata"), dict) else {}
            event_date = _safe_date(d.get("date")) or filing_date
            event_name = str(dmeta.get("timeline_title") or d.get("title") or f"Case Event {idx}")
            event_desc = str(dmeta.get("timeline_description") or d.get("summary") or "").strip() or None
            raw_type = str(dmeta.get("event_type") or "order").lower()
            event_type = EventType.OTHER
            for et in EventType:
                if et.value == raw_type:
                    event_type = et
                    break

            timeline.append(
                TimelineEvent(
                    id=str(d.get("id") or f"{case_number}-{idx}"),
                    date=event_date,
                    event_type=event_type,
                    title=event_name,
                    description=event_desc,
                    documents=[str(d.get("id") or "")],
                )
            )

        case_id = hashlib.sha1(case_number.encode("utf-8")).hexdigest()[:16]

        cases.append(
            CaseHistory(
                id=case_id,
                case_number=case_number,
                title=str(first.get("title") or case_number),
                court=_normalize_court(first.get("court")),
                bench=str(metadata_latest.get("bench")) if metadata_latest.get("bench") else None,
                status=_as_case_status(metadata_latest.get("case_status") or latest.get("status")),
                filing_date=filing_date,
                next_hearing=next_hearing,
                parties=parties,
                subject_matter=[str(x) for x in subject_matter if str(x).strip()],
                acts_sections=[str(x) for x in acts_sections if str(x).strip()],
                timeline=timeline,
                related_cases=[str(x) for x in related_cases if str(x).strip()],
                notes=str(metadata_latest.get("case_note")) if metadata_latest.get("case_note") else None,
            )
        )

    return sorted(cases, key=lambda c: c.filing_date, reverse=True)


def _try_build_cases_from_supabase() -> list["CaseHistory"]:
    """Primary case source from Supabase documents table."""
    try:
        from collections import defaultdict
        from junior.db.client import get_supabase_client

        client = get_supabase_client()
        if not client.is_configured:
            return []

        result = (
            client.documents
            .select("id,title,court,case_number,judgment_date,summary,legal_status,metadata,parties,keywords,legal_provisions")
            .order("judgment_date", desc=False)
            .limit(1000)
            .execute()
        )

        rows = result.data or []
        if not rows:
            return []

        grouped: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            if not isinstance(row, dict):
                continue
            if _is_demo_seed_document_id(row.get("id")):
                continue
            case_number = str(row.get("case_number") or "").strip()
            if not case_number:
                continue

            grouped[case_number].append(
                {
                    "id": row.get("id"),
                    "title": row.get("title"),
                    "court": row.get("court"),
                    "date": row.get("judgment_date"),
                    "summary": row.get("summary"),
                    "status": row.get("legal_status"),
                    "parties": row.get("parties") if isinstance(row.get("parties"), dict) else {},
                    "metadata": row.get("metadata") if isinstance(row.get("metadata"), dict) else {},
                    "keywords": row.get("keywords") if isinstance(row.get("keywords"), list) else [],
                    "legal_provisions": row.get("legal_provisions") if isinstance(row.get("legal_provisions"), list) else [],
                }
            )

        return _build_cases_from_grouped_docs(grouped)
    except Exception:
        return []


def _try_build_cases_from_local_store() -> list[CaseHistory]:
    """Best-effort case list from locally stored documents.

    This avoids serving hardcoded mock/demo cases. If there are no uploaded
    case documents, returns an empty list.
    """
    try:
        from pathlib import Path
        import json
        from collections import defaultdict

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

        return _build_cases_from_grouped_docs(grouped)
    except Exception:
        return []


def _load_cases() -> list[CaseHistory]:
    """Merged case source: Supabase (without seed demo rows) + local store."""
    merged: dict[str, CaseHistory] = {}

    # Local cases are always included so uploaded/manual local documents are visible.
    for case in _try_build_cases_from_local_store():
        merged[case.case_number] = case

    # Supabase cases override same case_number to keep DB as system of record.
    for case in _try_build_cases_from_supabase():
        merged[case.case_number] = case

    return sorted(merged.values(), key=lambda c: c.filing_date, reverse=True)

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


class CaseNoteUpsertRequest(BaseModel):
    note: str
    title: Optional[str] = None
    tag: Optional[str] = None


def _append_case_note(existing: Optional[str], note: str, title: Optional[str], tag: Optional[str]) -> str:
    clean_note = note.strip()
    if not clean_note:
        return (existing or "").strip()

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    label = title.strip() if title and title.strip() else "Case Note"
    if tag and tag.strip():
        label = f"{label} [{tag.strip()}]"

    block = f"{label} ({timestamp})\n{clean_note}"
    if existing and existing.strip():
        return f"{existing.strip()}\n\n---\n\n{block}"
    return block


def _save_case_note_local(case_number: str, note: str, title: Optional[str], tag: Optional[str]) -> bool:
    docs_dir = Path("uploads") / "documents"
    if not docs_dir.exists():
        return False

    matching: list[tuple[datetime, Path]] = []
    for fp in docs_dir.glob("*.json"):
        try:
            payload = json.loads(fp.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                continue
            if str(payload.get("case_number") or "").strip() != case_number:
                continue
            dt = _safe_date(payload.get("date"))
            sort_dt = datetime.combine(dt, datetime.min.time()) if dt else datetime.fromtimestamp(fp.stat().st_mtime)
            matching.append((sort_dt, fp))
        except Exception:
            continue

    if not matching:
        return False

    matching.sort(key=lambda x: x[0], reverse=True)
    target = matching[0][1]
    payload = json.loads(target.read_text(encoding="utf-8"))
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    merged_note = _append_case_note(metadata.get("case_note"), note, title, tag)
    metadata["case_note"] = merged_note
    payload["metadata"] = metadata
    target.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return True


def _save_case_note_supabase(case_number: str, note: str, title: Optional[str], tag: Optional[str]) -> bool:
    try:
        from junior.db.client import get_supabase_client

        client = get_supabase_client()
        if not client.is_configured:
            return False

        result = (
            client.documents
            .select("id,metadata,judgment_date,created_at")
            .eq("case_number", case_number)
            .order("judgment_date", desc=True)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return False

        row = rows[0] if isinstance(rows[0], dict) else {}
        doc_id = row.get("id")
        if not doc_id:
            return False

        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        metadata["case_note"] = _append_case_note(metadata.get("case_note"), note, title, tag)

        (
            client.documents
            .update({"metadata": metadata})
            .eq("id", doc_id)
            .execute()
        )
        return True
    except Exception:
        return False





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
    filtered = _load_cases()
    
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
    for case in _load_cases():
        if case.id == case_id:
            return case
    
    raise HTTPException(status_code=404, detail="Case not found")


@router.post("/search", response_model=CaseListResponse)
async def search_cases(request: CaseSearchRequest):
    """
    Advanced search for cases.
    """
    filtered = _load_cases()
    
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
    for case in _load_cases():
        if case.id == case_id:
            return case.timeline

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
    for case in _load_cases():
        if case.id == case_id:
            return {"case_id": case_id, "related_cases": case.related_cases}

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
    
    upcoming = []
    for c in _load_cases():
        if c.next_hearing and today <= c.next_hearing <= end_date:
            upcoming.append(
                {
                    "case_id": c.id,
                    "case_number": c.case_number,
                    "title": c.title,
                    "court": c.court,
                    "hearing_date": c.next_hearing,
                }
            )
    
    upcoming.sort(key=lambda x: x["hearing_date"])
    
    return {
        "from_date": today,
        "to_date": end_date,
        "hearings": upcoming
    }


@router.post("/{case_id}/notes")
async def save_case_note(case_id: str, request: CaseNoteUpsertRequest):
    """Persist a note on the selected case for cross-view reuse (analytics, strategy, etc.)."""
    note = (request.note or "").strip()
    if not note:
        raise HTTPException(status_code=400, detail="Note cannot be empty")

    selected_case = next((c for c in _load_cases() if c.id == case_id), None)
    if not selected_case:
        raise HTTPException(status_code=404, detail="Case not found")

    case_number = selected_case.case_number
    saved_supabase = _save_case_note_supabase(case_number, note, request.title, request.tag)
    saved_local = _save_case_note_local(case_number, note, request.title, request.tag)

    if not saved_supabase and not saved_local:
        raise HTTPException(
            status_code=503,
            detail="Unable to persist note for this case in either Supabase or local store",
        )

    append_audit_event(
        AuditEvent(
            event_type="case.note.upsert",
            actor="advocate",
            target=f"case:{case_number}",
            case_id=case_id,
            details={
                "title": request.title,
                "tag": request.tag,
                "length": len(note),
                "saved_supabase": saved_supabase,
                "saved_local": saved_local,
            },
        )
    )

    return {
        "case_id": case_id,
        "case_number": case_number,
        "saved": True,
        "saved_to": {
            "supabase": saved_supabase,
            "local": saved_local,
        },
    }
