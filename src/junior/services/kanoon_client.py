"""
Indian Kanoon API Client — Live case law search for Junior AI

Indian Kanoon (indiankanoon.org) is the largest free Indian legal database.
Their official API: https://api.indiankanoon.org/

API requires a token (free for research use). Get one at:
  https://api.indiankanoon.org/  →  "Sign Up for API"

Set INDIAN_KANOON_API_KEY in your .env file.

Features:
- Full-text search across SC, HC, Tribunals, Acts
- Fetch judgment metadata and full text
- Citation network (what cases cite this one)
- Filter by court, year range, doc type
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any, Optional
import json

from junior.core import get_logger, settings

logger = get_logger(__name__)

_KANOON_BASE = "https://api.indiankanoon.org"
_TIMEOUT_S = 15  # seconds per request


@dataclass
class KanoonResult:
    """A single result from Indian Kanoon."""
    doc_id: str
    title: str
    court: str
    date: str
    headline: str          # Short snippet / abstract
    url: str
    relevance_score: float = 0.0
    full_text: Optional[str] = None
    citations_in: list[str] = field(default_factory=list)   # cited by others
    citations_out: list[str] = field(default_factory=list)  # cites these


class KanoonClient:
    """
    Client for the Indian Kanoon REST API.

    All methods are async and return typed dataclasses.
    Falls back gracefully when no API key is configured.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "indian_kanoon_api_key", "") or ""
        self._available = bool(self.api_key)
        self._fallback = None  # FreeLegalClient — initialised lazily below

        if not self._available:
            logger.info(
                "[Kanoon] No INDIAN_KANOON_API_KEY — activating free scraper fallback "
                "(Indian Kanoon website + SC portal + Live Law + Bar & Bench RSS)."
            )
            # Lazy import avoids circular import (free_legal_sources imports KanoonResult)
            try:
                from junior.services.free_legal_sources import get_free_legal_client
                self._fallback = get_free_legal_client()
            except Exception as e:
                logger.warning(f"[Kanoon] Could not load free fallback: {e}")

    @property
    def is_available(self) -> bool:
        # Available if API key is set OR if the free scraper fallback loaded OK
        return self._available or self._fallback is not None

    @property
    def using_free_scraper(self) -> bool:
        """True when running without an API key (free scraper mode)."""
        return not self._available and self._fallback is not None

    async def search(
        self,
        query: str,
        page: int = 0,
        doc_types: Optional[list[str]] = None,
        from_year: Optional[int] = None,
        to_year: Optional[int] = None,
        max_results: int = 10,
    ) -> list[KanoonResult]:
        """
        Search Indian Kanoon for judgments matching `query`.

        Args:
            query:       Full-text search query (supports Boolean operators)
            page:        Page number for pagination (0-indexed)
            doc_types:   Filter by doc type, e.g. ["judgment", "act", "rules"]
            from_year:   Earliest year to include
            to_year:     Latest year to include
            max_results: Maximum results to return (API max: 10 per page)

        Returns:
            List of KanoonResult objects
        """
        if not self._available:
            if self._fallback:
                return await self._fallback.search(
                    query=query,
                    max_results=max_results,
                    from_year=from_year,
                    to_year=to_year,
                )
            return []

        params: dict[str, Any] = {
            "formInput": query,
            "pagenum": page,
        }
        if doc_types:
            params["doctypes"] = ",".join(doc_types)
        if from_year:
            params["fromdate"] = f"1-1-{from_year}"
        if to_year:
            params["todate"] = f"31-12-{to_year}"

        try:
            data = await self._post("/search/", params)
        except Exception as e:
            logger.warning(f"[Kanoon] Search failed: {e}")
            return []

        docs = data.get("docs", []) if isinstance(data, dict) else []
        results: list[KanoonResult] = []
        for item in docs[:max_results]:
            try:
                results.append(KanoonResult(
                    doc_id=str(item.get("tid", "")),
                    title=_strip_html(str(item.get("title", ""))),
                    court=str(item.get("docsource", "")),
                    date=str(item.get("publishdate", "")),
                    headline=_strip_html(str(item.get("headline", ""))),
                    url=f"https://indiankanoon.org/doc/{item.get('tid', '')}/",
                    relevance_score=float(item.get("relevance", 0.0)),
                ))
            except Exception as e:
                logger.debug(f"[Kanoon] Skipping malformed result: {e}")
                continue

        logger.info(f"[Kanoon] '{query[:60]}' → {len(results)} results")
        return results

    async def get_document(self, doc_id: str) -> Optional[KanoonResult]:
        """
        Fetch the full text and metadata of a specific document.

        Args:
            doc_id: Indian Kanoon document ID (tid)

        Returns:
            KanoonResult with full_text populated, or None on failure
        """
        if not self._available:
            if self._fallback:
                return await self._fallback.get_document(doc_id)
            return None

        try:
            data = await self._post(f"/doc/{doc_id}/", {})
        except Exception as e:
            logger.warning(f"[Kanoon] Fetch doc {doc_id} failed: {e}")
            return None

        if not isinstance(data, dict):
            return None

        return KanoonResult(
            doc_id=doc_id,
            title=_strip_html(str(data.get("title", ""))),
            court=str(data.get("docsource", "")),
            date=str(data.get("publishdate", "")),
            headline=_strip_html(str(data.get("headenote", ""))[:500]),
            url=f"https://indiankanoon.org/doc/{doc_id}/",
            full_text=_strip_html(str(data.get("doc", ""))),
            citations_out=[str(c) for c in data.get("citeList", [])],
        )

    async def get_citing_documents(self, doc_id: str, limit: int = 5) -> list[KanoonResult]:
        """
        Find judgments that cite the given document (forward citation network).

        Useful for checking if a case has been affirmed, followed, or overruled.
        """
        if not self._available:
            return []  # citation network not available without API key

        try:
            data = await self._post(f"/docfragment/{doc_id}/", {})
        except Exception as e:
            logger.warning(f"[Kanoon] Citing docs for {doc_id} failed: {e}")
            return []

        if not isinstance(data, dict):
            return []

        citing: list[KanoonResult] = []
        for item in (data.get("citedInDocs") or [])[:limit]:
            try:
                citing.append(KanoonResult(
                    doc_id=str(item.get("tid", "")),
                    title=_strip_html(str(item.get("title", ""))),
                    court=str(item.get("docsource", "")),
                    date=str(item.get("publishdate", "")),
                    headline="",
                    url=f"https://indiankanoon.org/doc/{item.get('tid', '')}/",
                ))
            except Exception:
                continue

        return citing

    async def search_section(self, act_name: str, section: str) -> list[KanoonResult]:
        """
        Convenience: search for judgments interpreting a specific statutory section.

        Example:
            results = await kanoon.search_section("Indian Penal Code", "Section 302")
        """
        query = f'"{act_name}" "{section}"'
        return await self.search(query, doc_types=["judgment"], max_results=10)

    # ------------------------------------------------------------------
    # Internal HTTP helper
    # ------------------------------------------------------------------

    async def _post(self, endpoint: str, params: dict) -> Any:
        """Make an authenticated POST request to the Kanoon API."""
        import urllib.parse
        import urllib.request

        url = _KANOON_BASE.rstrip("/") + endpoint
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        body = urllib.parse.urlencode(params).encode("utf-8")

        # Run in thread so we don't block the event loop
        def _do_request() -> bytes:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
                return resp.read()

        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(None, _do_request)
        return json.loads(raw)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def _strip_html(text: str) -> str:
    """Remove HTML tags and normalise whitespace."""
    text = _HTML_TAG_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_kanoon_client: Optional[KanoonClient] = None


def get_kanoon_client() -> KanoonClient:
    """Return the global KanoonClient singleton."""
    global _kanoon_client
    if _kanoon_client is None:
        _kanoon_client = KanoonClient()
    return _kanoon_client
