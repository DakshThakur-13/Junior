"""
Persistent Memory Store — Cross-session conversation memory for Junior AI

Stores per-user conversation history, past queries, and cited cases on disk
as JSON so context survives server restarts. No external database required.

Storage layout (under .memory/):
  .memory/sessions/{session_id}.json     — full conversation history
  .memory/users/{user_id}/index.json     — lightweight summary of past sessions
  .memory/cases/{case_id}.json           — cached case summaries for fast re-use

Design principles:
  - Zero dependencies beyond stdlib (json, pathlib, datetime)
  - Thread-safe writes via atomic rename pattern
  - Auto-prune: conversations older than MAX_AGE_DAYS are deleted
  - Max per-user: 50 sessions stored (FIFO eviction)
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from junior.core import get_logger

logger = get_logger(__name__)

MAX_AGE_DAYS = 30
MAX_SESSIONS_PER_USER = 50
MAX_MESSAGES_PER_SESSION = 200
_BASE_DIR = Path(".memory")


def _atomic_write(path: Path, data: dict) -> None:
    """Write JSON atomically to avoid torn reads."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=".tmp_")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _safe_read(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"Memory read failed [{path}]: {e}")
        return None


class MemoryStore:
    """
    Persistent memory for Junior AI legal conversations.

    Usage:
        store = MemoryStore()

        # Start / resume session
        session_id = store.new_session(user_id="user_abc", title="Bail query")

        # Add turns
        store.add_message(session_id, role="user", content="What is Section 438 CrPC?")
        store.add_message(session_id, role="assistant", content="Section 438 provides...")

        # Load history for context injection
        history = store.get_history(session_id, last_n=10)

        # Summarise past queries for a user
        past = store.get_user_sessions(user_id="user_abc")
    """

    def __init__(self, base_dir: Path | str = _BASE_DIR):
        self.base_dir = Path(base_dir)
        self.sessions_dir = self.base_dir / "sessions"
        self.users_dir = self.base_dir / "users"
        self.cases_dir = self.base_dir / "cases"
        for d in (self.sessions_dir, self.users_dir, self.cases_dir):
            d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def new_session(
        self,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        session_type: str = "general",
    ) -> str:
        """Create a new conversation session and return its ID."""
        session_id = str(uuid4())
        data = {
            "session_id": session_id,
            "user_id": user_id,
            "title": title or "Untitled session",
            "session_type": session_type,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "messages": [],
            "cited_cases": [],
            "metadata": {},
        }
        _atomic_write(self.sessions_dir / f"{session_id}.json", data)
        logger.info(f"[Memory] New session {session_id} for user {user_id}")

        if user_id:
            self._update_user_index(user_id, session_id, title or "Untitled session")

        return session_id

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Append a message to a session (auto-creates session if missing)."""
        path = self.sessions_dir / f"{session_id}.json"
        data = _safe_read(path)
        if data is None:
            data = {
                "session_id": session_id,
                "user_id": None,
                "title": "Auto-recovered session",
                "session_type": "general",
                "created_at": datetime.utcnow().isoformat(),
                "messages": [],
                "cited_cases": [],
                "metadata": {},
            }

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        data["messages"].append(message)
        data["updated_at"] = datetime.utcnow().isoformat()

        # Prune if too long (keep latest)
        if len(data["messages"]) > MAX_MESSAGES_PER_SESSION:
            data["messages"] = data["messages"][-MAX_MESSAGES_PER_SESSION:]

        _atomic_write(path, data)

    def get_history(
        self,
        session_id: str,
        last_n: int = 20,
    ) -> list[dict[str, str]]:
        """Return the last N messages as [{role, content}] dicts."""
        path = self.sessions_dir / f"{session_id}.json"
        data = _safe_read(path)
        if not data:
            return []
        messages = data.get("messages", [])[-last_n:]
        return [{"role": m["role"], "content": m["content"]} for m in messages]

    def get_session(self, session_id: str) -> Optional[dict]:
        """Return full session data."""
        return _safe_read(self.sessions_dir / f"{session_id}.json")

    def update_session_title(self, session_id: str, title: str) -> None:
        """Update the display title of a session."""
        path = self.sessions_dir / f"{session_id}.json"
        data = _safe_read(path)
        if data:
            data["title"] = title
            data["updated_at"] = datetime.utcnow().isoformat()
            _atomic_write(path, data)

    def add_cited_case(self, session_id: str, case: dict) -> None:
        """Record a case citation used in this session."""
        path = self.sessions_dir / f"{session_id}.json"
        data = _safe_read(path)
        if data is None:
            return
        cited = data.setdefault("cited_cases", [])
        case_id = case.get("case_name", "") + str(case.get("year", ""))
        if not any(
            c.get("case_name") == case.get("case_name") and c.get("year") == case.get("year")
            for c in cited
        ):
            cited.append(case)
        _atomic_write(path, data)

    # ------------------------------------------------------------------
    # User-level index
    # ------------------------------------------------------------------

    def get_user_sessions(self, user_id: str, limit: int = 20) -> list[dict]:
        """Return recent session summaries for a user (newest first)."""
        index = self._load_user_index(user_id)
        sessions = index.get("sessions", [])
        # Sort newest first
        sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
        return sessions[:limit]

    def get_user_cited_cases(self, user_id: str) -> list[str]:
        """Return a de-duplicated list of case names cited across all user sessions."""
        seen: set[str] = set()
        for summary in self.get_user_sessions(user_id, limit=MAX_SESSIONS_PER_USER):
            sid = summary.get("session_id", "")
            data = _safe_read(self.sessions_dir / f"{sid}.json")
            if data:
                for c in data.get("cited_cases", []):
                    name = c.get("case_name", "")
                    if name:
                        seen.add(name)
        return sorted(seen)

    # ------------------------------------------------------------------
    # Case summary cache
    # ------------------------------------------------------------------

    def cache_case_summary(self, case_id: str, summary: dict) -> None:
        """Store a case summary for fast retrieval without re-querying the LLM."""
        _atomic_write(self.cases_dir / f"{case_id}.json", {
            **summary,
            "cached_at": datetime.utcnow().isoformat(),
        })

    def get_case_summary(self, case_id: str) -> Optional[dict]:
        """Retrieve a cached case summary."""
        return _safe_read(self.cases_dir / f"{case_id}.json")

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def prune_old_sessions(self) -> int:
        """Delete sessions older than MAX_AGE_DAYS. Returns count deleted."""
        cutoff = datetime.utcnow() - timedelta(days=MAX_AGE_DAYS)
        deleted = 0
        for path in self.sessions_dir.glob("*.json"):
            data = _safe_read(path)
            if not data:
                continue
            updated_str = data.get("updated_at", "")
            try:
                updated = datetime.fromisoformat(updated_str)
                if updated < cutoff:
                    path.unlink(missing_ok=True)
                    deleted += 1
            except Exception:
                continue
        logger.info(f"[Memory] Pruned {deleted} old sessions")
        return deleted

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_user_index(self, user_id: str) -> dict:
        path = self.users_dir / user_id / "index.json"
        return _safe_read(path) or {"user_id": user_id, "sessions": []}

    def _update_user_index(self, user_id: str, session_id: str, title: str) -> None:
        index = self._load_user_index(user_id)
        sessions: list[dict] = index.setdefault("sessions", [])

        # Remove existing entry for this session_id if present
        sessions = [s for s in sessions if s.get("session_id") != session_id]

        sessions.append({
            "session_id": session_id,
            "title": title,
            "updated_at": datetime.utcnow().isoformat(),
        })

        # FIFO eviction if too many
        if len(sessions) > MAX_SESSIONS_PER_USER:
            # Drop oldest
            sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
            sessions = sessions[:MAX_SESSIONS_PER_USER]

        index["sessions"] = sessions
        _atomic_write(self.users_dir / user_id / "index.json", index)


# ---------------------------------------------------------------------------
# Module-level singleton (lazy init)
# ---------------------------------------------------------------------------
_memory_store: Optional[MemoryStore] = None


def get_memory_store() -> MemoryStore:
    """Return the global MemoryStore singleton."""
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore()
    return _memory_store
