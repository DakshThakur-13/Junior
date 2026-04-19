"""Case workbench endpoints: tasks, reminders, and quick global search."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
from uuid import uuid4
import json

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from junior.services.audit_log import AuditEvent, append_audit_event
from .cases import _load_cases

router = APIRouter()

_WORKBENCH_DIR = Path("uploads") / "workbench"


class CaseTask(BaseModel):
    id: str
    title: str
    status: str = "open"  # open | in_progress | blocked | done
    priority: str = "medium"  # low | medium | high | critical
    owner: Optional[str] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    status: str = "open"
    priority: str = "medium"
    owner: Optional[str] = Field(default=None, max_length=120)
    due_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=5000)


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    status: Optional[str] = None
    priority: Optional[str] = None
    owner: Optional[str] = Field(default=None, max_length=120)
    due_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=5000)


class TaskListResponse(BaseModel):
    case_id: str
    case_number: str
    tasks: list[CaseTask]
    alerts: list[dict] = Field(default_factory=list)


class WorkbenchSearchResponse(BaseModel):
    query: str
    cases: list[dict] = Field(default_factory=list)
    documents: list[dict] = Field(default_factory=list)


def _case_by_id(case_id: str):
    return next((c for c in _load_cases() if c.id == case_id), None)


def _workbench_path(case_id: str) -> Path:
    _WORKBENCH_DIR.mkdir(parents=True, exist_ok=True)
    return _WORKBENCH_DIR / f"{case_id}.json"


def _load_case_tasks(case_id: str) -> list[CaseTask]:
    fp = _workbench_path(case_id)
    if not fp.exists():
        return []

    try:
        payload = json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return []

    raw_tasks = payload.get("tasks") if isinstance(payload, dict) else None
    if not isinstance(raw_tasks, list):
        return []

    tasks: list[CaseTask] = []
    for item in raw_tasks:
        if not isinstance(item, dict):
            continue
        try:
            tasks.append(CaseTask(**item))
        except Exception:
            continue
    tasks.sort(key=lambda t: (t.status == "done", t.due_date or date.max, t.created_at))
    return tasks


def _save_case_tasks(case_id: str, tasks: list[CaseTask]) -> None:
    fp = _workbench_path(case_id)
    payload = {
        "case_id": case_id,
        "updated_at": datetime.utcnow().isoformat(),
        "tasks": [t.model_dump(mode="json") for t in tasks],
    }
    fp.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def _build_alerts(tasks: list[CaseTask]) -> list[dict]:
    now = date.today()
    soon = now + timedelta(days=3)

    alerts: list[dict] = []
    for task in tasks:
        if task.status == "done" or not task.due_date:
            continue
        if task.due_date < now:
            alerts.append({
                "type": "overdue",
                "task_id": task.id,
                "title": task.title,
                "due_date": str(task.due_date),
                "severity": "high" if task.priority in {"high", "critical"} else "medium",
            })
        elif task.due_date <= soon:
            alerts.append({
                "type": "upcoming",
                "task_id": task.id,
                "title": task.title,
                "due_date": str(task.due_date),
                "severity": "medium",
            })

    return alerts


@router.get("/{case_id}/tasks", response_model=TaskListResponse)
async def list_tasks(case_id: str):
    selected_case = _case_by_id(case_id)
    if not selected_case:
        raise HTTPException(status_code=404, detail="Case not found")

    tasks = _load_case_tasks(case_id)
    return TaskListResponse(
        case_id=case_id,
        case_number=selected_case.case_number,
        tasks=tasks,
        alerts=_build_alerts(tasks),
    )


@router.post("/{case_id}/tasks", response_model=TaskListResponse)
async def create_task(case_id: str, request: TaskCreateRequest):
    selected_case = _case_by_id(case_id)
    if not selected_case:
        raise HTTPException(status_code=404, detail="Case not found")

    task = CaseTask(
        id=str(uuid4()),
        title=request.title.strip(),
        status=(request.status or "open").strip().lower(),
        priority=(request.priority or "medium").strip().lower(),
        owner=(request.owner or "").strip() or None,
        due_date=request.due_date,
        notes=(request.notes or "").strip() or None,
    )

    tasks = _load_case_tasks(case_id)
    tasks.append(task)
    _save_case_tasks(case_id, tasks)

    append_audit_event(
        AuditEvent(
            event_type="workbench.task.create",
            actor="advocate",
            target=f"case:{selected_case.case_number}",
            case_id=case_id,
            details={"task_id": task.id, "title": task.title, "priority": task.priority, "due_date": str(task.due_date) if task.due_date else None},
        )
    )

    return TaskListResponse(
        case_id=case_id,
        case_number=selected_case.case_number,
        tasks=tasks,
        alerts=_build_alerts(tasks),
    )


@router.patch("/{case_id}/tasks/{task_id}", response_model=TaskListResponse)
async def update_task(case_id: str, task_id: str, request: TaskUpdateRequest):
    selected_case = _case_by_id(case_id)
    if not selected_case:
        raise HTTPException(status_code=404, detail="Case not found")

    tasks = _load_case_tasks(case_id)
    idx = next((i for i, t in enumerate(tasks) if t.id == task_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Task not found")

    current = tasks[idx]
    updated = current.model_copy(
        update={
            "title": request.title.strip() if isinstance(request.title, str) and request.title.strip() else current.title,
            "status": request.status.strip().lower() if isinstance(request.status, str) and request.status.strip() else current.status,
            "priority": request.priority.strip().lower() if isinstance(request.priority, str) and request.priority.strip() else current.priority,
            "owner": request.owner.strip() if isinstance(request.owner, str) and request.owner.strip() else current.owner,
            "due_date": request.due_date if request.due_date is not None else current.due_date,
            "notes": request.notes.strip() if isinstance(request.notes, str) and request.notes.strip() else current.notes,
            "updated_at": datetime.utcnow(),
        }
    )
    tasks[idx] = updated
    _save_case_tasks(case_id, tasks)

    append_audit_event(
        AuditEvent(
            event_type="workbench.task.update",
            actor="advocate",
            target=f"case:{selected_case.case_number}",
            case_id=case_id,
            details={
                "task_id": task_id,
                "status": updated.status,
                "priority": updated.priority,
                "owner": updated.owner,
                "due_date": str(updated.due_date) if updated.due_date else None,
            },
        )
    )

    return TaskListResponse(
        case_id=case_id,
        case_number=selected_case.case_number,
        tasks=tasks,
        alerts=_build_alerts(tasks),
    )


@router.get("/search", response_model=WorkbenchSearchResponse)
async def workbench_search(query: str = Query(..., min_length=2, max_length=200), limit: int = Query(20, ge=1, le=100)):
    q = query.strip().lower()
    if not q:
        return WorkbenchSearchResponse(query=query)

    cases = _load_cases()
    case_hits: list[dict] = []
    for case in cases:
        hay = " ".join([
            case.title,
            case.case_number,
            case.court,
            " ".join(case.subject_matter),
            " ".join(case.acts_sections),
            case.notes or "",
        ]).lower()
        if q in hay:
            case_hits.append(
                {
                    "id": case.id,
                    "case_number": case.case_number,
                    "title": case.title,
                    "court": case.court,
                    "status": case.status.value,
                }
            )

    document_hits: list[dict] = []
    docs_dir = Path("uploads") / "documents"
    if docs_dir.exists():
        for fp in docs_dir.glob("*.json"):
            try:
                payload = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            title = str(payload.get("title") or "")
            summary = str(payload.get("summary") or "")
            case_number = str(payload.get("case_number") or "")
            hay = f"{title} {summary} {case_number}".lower()
            if q not in hay:
                continue
            document_hits.append(
                {
                    "id": str(payload.get("id") or fp.stem),
                    "title": title or "Untitled Document",
                    "case_number": case_number,
                    "source": "local",
                }
            )

    case_hits = case_hits[:limit]
    document_hits = document_hits[:limit]

    return WorkbenchSearchResponse(
        query=query,
        cases=case_hits,
        documents=document_hits,
    )
