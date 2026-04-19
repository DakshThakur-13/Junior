"""Append-only, tamper-evident audit logging for legal workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Optional
import json

from junior.core import get_logger

logger = get_logger(__name__)

_AUDIT_DIR = Path("uploads") / "audit"
_AUDIT_FILE = _AUDIT_DIR / "events.jsonl"


@dataclass
class AuditEvent:
    event_type: str
    actor: str
    target: str
    details: dict[str, Any]
    case_id: Optional[str] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _last_hash() -> str:
    if not _AUDIT_FILE.exists():
        return "GENESIS"

    try:
        with _AUDIT_FILE.open("r", encoding="utf-8") as fh:
            last_line = ""
            for line in fh:
                if line.strip():
                    last_line = line
        if not last_line:
            return "GENESIS"
        payload = json.loads(last_line)
        return str(payload.get("hash") or "GENESIS")
    except Exception as exc:
        logger.warning(f"Audit log read failed: {exc}")
        return "GENESIS"


def _compute_hash(record: dict[str, Any], previous_hash: str) -> str:
    canonical = json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return sha256(f"{previous_hash}:{canonical}".encode("utf-8")).hexdigest()


def append_audit_event(event: AuditEvent) -> dict[str, Any]:
    """Persist one append-only audit event with a hash chain."""
    _AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    record: dict[str, Any] = {
        "timestamp": _now_iso(),
        "event_type": event.event_type,
        "actor": event.actor or "system",
        "target": event.target,
        "case_id": event.case_id,
        "details": event.details,
    }
    prev = _last_hash()
    record["prev_hash"] = prev
    record["hash"] = _compute_hash(record, prev)

    with _AUDIT_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=True) + "\n")

    return record


def recent_audit_events(limit: int = 100, case_id: Optional[str] = None) -> list[dict[str, Any]]:
    if not _AUDIT_FILE.exists():
        return []

    cap = max(1, min(limit, 1000))
    rows: list[dict[str, Any]] = []

    with _AUDIT_FILE.open("r", encoding="utf-8") as fh:
        for line in fh:
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
                if case_id and str(payload.get("case_id") or "") != case_id:
                    continue
                rows.append(payload)
            except Exception:
                continue

    rows.reverse()
    return rows[:cap]


def verify_audit_chain(limit: int = 5000) -> dict[str, Any]:
    """Validate hash-chain integrity for recorded events."""
    if not _AUDIT_FILE.exists():
        return {"ok": True, "checked": 0, "message": "No audit events yet"}

    checked = 0
    prev = "GENESIS"

    with _AUDIT_FILE.open("r", encoding="utf-8") as fh:
        for line in fh:
            if checked >= max(1, limit):
                break
            text = line.strip()
            if not text:
                continue
            checked += 1
            payload = json.loads(text)
            stored_hash = str(payload.get("hash") or "")
            stored_prev = str(payload.get("prev_hash") or "")

            canonical_payload = {k: v for k, v in payload.items() if k != "hash"}
            expected_hash = _compute_hash(canonical_payload, stored_prev)

            if stored_prev != prev:
                return {
                    "ok": False,
                    "checked": checked,
                    "message": "Hash chain broken (prev_hash mismatch)",
                }
            if stored_hash != expected_hash:
                return {
                    "ok": False,
                    "checked": checked,
                    "message": "Hash chain broken (hash mismatch)",
                }

            prev = stored_hash

    return {"ok": True, "checked": checked, "message": "Audit chain verified"}
