"""
Free Legal Sources — Unified Indian case law search with zero API keys required.

Merges Option 2 (free public alternatives) + Option 3 (web scrapers):

  Source 1 — Indian Kanoon Scraper
      Scrapes indiankanoon.org public HTML search (India's largest free legal DB).
      No API key, no login, works immediately.

  Source 2 — Supreme Court of India Website
      Scrapes main.sci.gov.in/judgements for SC judgments directly from the
      official government website.

  Source 3 — Live Law RSS Feed
      Parses https://www.livelaw.in/rss for breaking legal news and fresh
      judgment summaries from India's most-read legal news outlet.

  Source 4 — Bar & Bench RSS Feed
      Parses https://barandbench.com/feed — independent legal journalism with
      detailed judgment coverage.

  Source 5 — eCourts India (NJDG)
      Queries the National Judicial Data Grid at https://njdg.ecourts.gov.in
      for case pendency and disposal statistics (supplementary data).

All sources are searched in PARALLEL and results are merged + deduplicated
before being returned as the standard KanoonResult list used everywhere in
Junior.

Usage:
    from junior.services.free_legal_sources import get_free_legal_client

    client = get_free_legal_client()
    results = await client.search("Section 302 IPC murder bail conditions")
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────
# Re-use KanoonResult so the rest of Junior is
# agnostic about which source produced results.
# ─────────────────────────────────────────────────
from junior.services.kanoon_client import KanoonResult


# ══════════════════════════════════════════════════════════════════════════════
#  Shared HTTP helpers (httpx async — already installed)
# ══════════════════════════════════════════════════════════════════════════════

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Connection": "keep-alive",
}
_TIMEOUT = 20.0  # seconds


async def _get_html(url: str, params: Optional[dict] = None) -> str:
    """GETs a URL and returns the decoded HTML text. Returns '' on failure."""
    import httpx
    try:
        async with httpx.AsyncClient(
            headers=_BROWSER_HEADERS,
            timeout=_TIMEOUT,
            follow_redirects=True,
        ) as client:
            resp = await client.get(url, params=params or {})
            resp.raise_for_status()
            return resp.text
    except Exception as e:
        logger.debug(f"[FreeLegal] GET {url} failed: {e}")
        return ""


def _strip_html(text: str) -> str:
    """Remove HTML tags and normalise whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _as_text(value: object) -> str:
    """Safely coerce feedparser/bs4 mixed values to text."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        for key in ("value", "title", "link", "href"):
            raw = value.get(key)
            if isinstance(raw, str):
                return raw
        return ""
    if isinstance(value, list):
        for item in value:
            text = _as_text(item)
            if text:
                return text
        return ""
    return ""


def _content_hash(title: str) -> str:
    """Cheap deduplication key: normalised lowercase title hash."""
    normalised = re.sub(r"[^a-z0-9]", "", title.lower())
    return hashlib.md5(normalised.encode()).hexdigest()[:12]


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 1 — Indian Kanoon Public Website Scraper
# ══════════════════════════════════════════════════════════════════════════════

class KanoonScraper:
    """
    Scrapes indiankanoon.org public search — the same interface every Indian
    lawyer uses daily.  Works without any API key.

    The public search at https://indiankanoon.org/search/?formInput=<query>
    returns up to 10 results per page in a structured HTML format.
    """

    SEARCH_URL = "https://indiankanoon.org/search/"
    BASE_URL = "https://indiankanoon.org"

    # Hard limits to stay polite
    MAX_PAGES = 2
    DELAY_BETWEEN_PAGES = 1.0  # seconds

    async def search(
        self,
        query: str,
        max_results: int = 10,
        court_filter: Optional[str] = None,
    ) -> list[KanoonResult]:
        """Search Indian Kanoon free website, returning up to max_results."""
        results: list[KanoonResult] = []
        pages_needed = min(self.MAX_PAGES, (max_results + 9) // 10)

        for page in range(pages_needed):
            if page > 0:
                await asyncio.sleep(self.DELAY_BETWEEN_PAGES)

            params: dict = {"formInput": query, "pagenum": page}
            if court_filter:
                params["court"] = court_filter

            html = await _get_html(self.SEARCH_URL, params)
            if not html:
                break

            page_results = self._parse_results(html)
            results.extend(page_results)
            logger.info(
                f"[KanoonScraper] page={page} query='{query[:50]}' → {len(page_results)} results"
            )
            if len(page_results) < 10:  # last page
                break

        return results[:max_results]

    def _parse_results(self, html: str) -> list[KanoonResult]:
        """Parse search results from indiankanoon.org HTML (verified 2026 structure)."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        results: list[KanoonResult] = []

        # Results are <article class="result" role="listitem"> elements
        for article in soup.find_all("article", class_="result"):
            try:
                # ── Title + URL ──────────────────────────────────────────────
                h4 = article.find("h4", class_="result_title")
                title_a = h4.find("a") if h4 else article.find("a")
                if not title_a:
                    continue

                title = _strip_html(title_a.get_text())
                href = _as_text(title_a.get("href", ""))

                # Extract doc_id from /docfragment/{id}/ or /doc/{id}/
                doc_id_match = re.search(r"/(doc|docfragment)/(\d+)/", href)
                doc_id = doc_id_match.group(2) if doc_id_match else _content_hash(title)

                # Canonical URL always uses /doc/{id}/
                doc_url = f"{self.BASE_URL}/doc/{doc_id}/"

                # ── Snippet (div.headline) ────────────────────────────────────
                headline_div = article.find("div", class_="headline")
                snippet = _strip_html(headline_div.get_text()) if headline_div else ""

                # ── Court (span.docsource inside div.hlbottom) ───────────────
                court = ""
                hlbottom = article.find("div", class_="hlbottom")
                if hlbottom:
                    docsource_span = hlbottom.find("span", class_="docsource")
                    if docsource_span:
                        court = docsource_span.get_text(strip=True)

                # ── Date — embedded in the title ("on DD Month, YYYY") ───────
                date = ""
                date_match = re.search(r"on (\d{1,2} \w+ \d{4})", title)
                if date_match:
                    date = date_match.group(1)

                results.append(KanoonResult(
                    doc_id=doc_id,
                    title=title,
                    court=court,
                    date=date,
                    headline=snippet[:500],
                    url=doc_url,
                    relevance_score=0.85,
                ))
            except Exception as e:
                logger.debug(f"[KanoonScraper] Skipping malformed result: {e}")
                continue

        return results

    async def get_full_text(self, doc_url: str, max_chars: int = 8000) -> str:
        """Fetch the full judgment text from a case URL (for enriching results)."""
        html = await _get_html(doc_url)
        if not html:
            return ""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")

            # Main judgment content is in div#judgments
            judgment_div = soup.find("div", id="judgments")
            if not judgment_div:
                judgment_div = soup.find("div", class_="judgments")
            if judgment_div:
                return _strip_html(judgment_div.get_text())[:max_chars]
        except Exception as e:
            logger.debug(f"[KanoonScraper] full_text parse failed: {e}")
        return ""


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 2 — Supreme Court of India Official Website
# ══════════════════════════════════════════════════════════════════════════════

class SCWebsiteScraper:
    """
    Searches the Supreme Court of India's official judgment portal.
    URL: https://main.sci.gov.in/judgements
    Also uses the SC order portal at https://orders.sci.gov.in

    Only covers SC judgments (highest authority), so results are
    always binding on all Indian courts.
    """

    JUDGMENT_URL = "https://main.sci.gov.in/judgements"

    async def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[KanoonResult]:
        """Search SC judgment portal. Returns binding SC-only results."""
        # The SC portal search is at main.sci.gov.in with form submission.
        # We use the simpler judge search URL pattern.
        results: list[KanoonResult] = []
        try:
            html = await _get_html(
                self.JUDGMENT_URL,
                params={"searchphrase": query, "submit": "Search"},
            )
            if html:
                results = self._parse_sc_results(html, max_results)
                logger.info(f"[SCWebsite] query='{query[:50]}' → {len(results)} SC results")
        except Exception as e:
            logger.debug(f"[SCWebsite] search failed: {e}")
        return results

    def _parse_sc_results(self, html: str, max_results: int) -> list[KanoonResult]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        results: list[KanoonResult] = []

        # SC results appear in <table> rows or <div class="card">
        rows = soup.find_all("tr")[1:max_results + 1]  # skip header row
        for row in rows:
            try:
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue
                case_no = cells[0].get_text(strip=True) if cells else ""
                title = cells[1].get_text(strip=True) if len(cells) > 1 else case_no
                date = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                link = row.find("a")
                url = ""
                if link and link.get("href"):
                    href = _as_text(link.get("href"))
                    url = href if href.startswith("http") else "https://main.sci.gov.in" + href

                results.append(KanoonResult(
                    doc_id=_content_hash(title),
                    title=title or case_no,
                    court="Supreme Court of India",
                    date=date,
                    headline=f"Supreme Court judgment — {title}",
                    url=url or self.JUDGMENT_URL,
                    relevance_score=0.90,  # SC judgments get higher weight
                ))
            except Exception:
                continue
        return results


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 3 — Live Law RSS Feed
# ══════════════════════════════════════════════════════════════════════════════

class LiveLawRSSReader:
    """
    Reads Live Law RSS feed (https://www.livelaw.in/rss) and filters
    entries whose headline/summary matches the query.

    Live Law covers:
    - Supreme Court daily orders and judgments
    - High Court judgments
    - Tribunal orders
    - New legislation
    """

    FEEDS = [
        # Live Law RSS currently returns 404 on all paths (as of 2026-03)
        # Uncomment if they restore RSS:
        # ("LiveLaw SC",  "https://www.livelaw.in/supreme-court/rss"),
        # ("LiveLaw HC",  "https://www.livelaw.in/high-courts/rss"),
        #
        # Working alternatives:
        ("Bar & Bench",     "https://barandbench.com/feed"),
        ("Latest Laws",     "https://www.latestlaws.com/rss.xml"),
        ("Legally India",   "https://www.legallyindia.com/feed"),
    ]

    async def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[KanoonResult]:
        """Fetch all feeds in parallel and filter by query terms."""
        query_terms = {t.lower() for t in re.split(r"\W+", query) if len(t) > 3}

        async def _fetch_feed(label: str, url: str) -> list[KanoonResult]:
            html = await _get_html(url)
            if not html:
                return []
            return self._parse_feed(html, label, query_terms)

        tasks = [_fetch_feed(label, url) for label, url in self.FEEDS]
        all_lists = await asyncio.gather(*tasks, return_exceptions=True)

        combined: list[KanoonResult] = []
        for res in all_lists:
            if isinstance(res, list):
                combined.extend(res)

        # Sort by relevance (number of matching terms in title/summary)
        combined.sort(key=lambda r: r.relevance_score, reverse=True)
        logger.info(f"[LiveLaw] query='{query[:50]}' → {len(combined)} RSS matches")
        return combined[:max_results]

    def _parse_feed(
        self,
        xml: str,
        label: str,
        query_terms: set[str],
    ) -> list[KanoonResult]:
        """Parse RSS XML and return matching entries."""
        import feedparser  # lazy import
        feed = feedparser.parse(xml)
        results: list[KanoonResult] = []

        for entry in feed.entries:
            title = _as_text(entry.get("title", ""))
            summary = _strip_html(_as_text(entry.get("summary", "")))
            url = _as_text(entry.get("link", ""))
            published = _as_text(entry.get("published", ""))

            combined_text = (title + " " + summary).lower()
            matches = sum(1 for t in query_terms if t in combined_text)
            if matches == 0:
                continue
            relevance = min(0.80, 0.40 + (matches * 0.10))

            results.append(KanoonResult(
                doc_id=_content_hash(title),
                title=title,
                court=label,
                date=published[:10] if published else "",
                headline=summary[:400],
                url=url,
                relevance_score=relevance,
            ))

        return results


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 4 — Bar & Bench RSS Feed
# ══════════════════════════════════════════════════════════════════════════════

class BarAndBenchRSSReader:
    """
    Reads Bar & Bench RSS (https://barandbench.com/feed) and returns
    judgment-related entries matching the query.

    Bar & Bench specialises in detailed case law reporting and often
    publishes judgment summaries ahead of Live Law.
    """

    FEEDS = [
        # Only barandbench.com/feed works; /courts/*/feed paths return 404
        ("Bar & Bench", "https://barandbench.com/feed"),
    ]

    async def search(self, query: str, max_results: int = 5) -> list[KanoonResult]:
        query_terms = {t.lower() for t in re.split(r"\W+", query) if len(t) > 3}

        async def _fetch(label: str, url: str) -> list[KanoonResult]:
            xml = await _get_html(url)
            if not xml:
                return []
            return self._parse_feed(xml, label, query_terms)

        results: list[KanoonResult] = []
        all_lists = await asyncio.gather(
            *[_fetch(l, u) for l, u in self.FEEDS],
            return_exceptions=True,
        )
        seen: set[str] = set()
        for group in all_lists:
            if isinstance(group, list):
                for r in group:
                    if r.doc_id not in seen:
                        seen.add(r.doc_id)
                        results.append(r)

        results.sort(key=lambda r: r.relevance_score, reverse=True)
        logger.info(f"[Bar&Bench] query='{query[:50]}' → {len(results)} RSS matches")
        return results[:max_results]

    def _parse_feed(
        self,
        xml: str,
        label: str,
        query_terms: set[str],
    ) -> list[KanoonResult]:
        import feedparser
        feed = feedparser.parse(xml)
        results: list[KanoonResult] = []
        for entry in feed.entries:
            title = _as_text(entry.get("title", ""))
            content_value = _as_text(entry.get("content", ""))
            summary = _strip_html(_as_text(entry.get("summary", "")) or content_value)
            url = _as_text(entry.get("link", ""))
            published = _as_text(entry.get("published", ""))
            text = (title + " " + summary).lower()
            matches = sum(1 for t in query_terms if t in text)
            if matches == 0:
                continue
            results.append(KanoonResult(
                doc_id=_content_hash(title),
                title=title,
                court=label,
                date=published[:10] if published else "",
                headline=summary[:400],
                url=url,
                relevance_score=min(0.75, 0.35 + matches * 0.10),
            ))
        return results


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 5 — eCourts India / NJDG (National Judicial Data Grid)
# ══════════════════════════════════════════════════════════════════════════════

class ECourtsClient:
    """
    Queries the National Judicial Data Grid (https://njdg.ecourts.gov.in).
    NJDG is a government portal tracking case pendency across all courts.

    This supplements case-specific searches with:
    - Court-level statistics
    - Act/section wise case counts (helps gauge importance of a section)
    - Judge-wise disposal data

    Note: eCourts requires login for judgment PDFs. We use only
    the public-facing NJDG endpoints here.
    """

    NJDG_BASE = "https://njdg.ecourts.gov.in/njdgnew"
    SECTION_STATS_URL = "https://njdg.ecourts.gov.in/njdgnew/index.php"

    async def get_act_stats(self, act_query: str) -> dict:
        """
        Get case pendency statistics for a legal act/section.
        Returns a dict suitable for injecting into the researcher's context.
        """
        try:
            html = await _get_html(
                self.SECTION_STATS_URL,
                params={"p": "main", "act": act_query},
            )
            if not html:
                return {}
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")

            stats: dict = {}
            # Try to find total case counts in any stat table
            for table in soup.find_all("table"):
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True)
                        val = cells[1].get_text(strip=True)
                        if key and val:
                            stats[key] = val
            logger.info(f"[eCourts] Stats for '{act_query}': {len(stats)} entries")
            return stats
        except Exception as e:
            logger.debug(f"[eCourts] Stats failed: {e}")
            return {}


# ══════════════════════════════════════════════════════════════════════════════
#  UNIFIED FREE LEGAL CLIENT — Merges all sources
# ══════════════════════════════════════════════════════════════════════════════

class FreeLegalClient:
    """
    Aggregates Indian Kanoon scraper + Supreme Court website + Live Law RSS
    + Bar & Bench RSS into a single async interface that matches the
    official KanoonClient API.

    Used as automatic fallback when INDIAN_KANOON_API_KEY is not set.

    Search strategy:
    1. All four sources searched IN PARALLEL (asyncio.gather)
    2. Results deduplicated by normalised title hash
    3. Sorted: SC judgments first, then by relevance score
    4. Top N returned
    """

    def __init__(self):
        self._kanoon  = KanoonScraper()
        self._sc      = SCWebsiteScraper()
        self._livelaw = LiveLawRSSReader()
        self._bb      = BarAndBenchRSSReader()
        self._ecourts = ECourtsClient()
        logger.info(
            "[FreeLegalClient] Initialised — using 4 free sources: "
            "Indian Kanoon scraper, SC website, Live Law RSS, Bar & Bench RSS"
        )

    @property
    def is_available(self) -> bool:
        return True  # always available — no API key needed

    async def search(
        self,
        query: str,
        max_results: int = 10,
        doc_types: Optional[list[str]] = None,
        from_year: Optional[int] = None,
        to_year: Optional[int] = None,
    ) -> list[KanoonResult]:
        """
        Search all free sources in parallel and return merged results.

        Args:
            query:       Legal search query (same as KanoonClient.search)
            max_results: Maximum results to return
            doc_types:   Currently unused (all sources return judgments)
            from_year:   Filter results newer than this year (best-effort)
            to_year:     Filter results up to this year (best-effort)

        Returns:
            Deduplicated list of KanoonResult sorted by court authority + score
        """
        # Per-source budgets: kanoon gets more slots since it's comprehensive
        kanoon_n  = min(max_results, 8)
        sc_n      = min(max_results, 4)
        livelaw_n = min(max_results, 4)
        bb_n      = min(max_results, 3)

        # Fire all sources in parallel
        kanoon_res, sc_res, ll_res, bb_res = await asyncio.gather(
            self._kanoon.search(query, max_results=kanoon_n),
            self._sc.search(query, max_results=sc_n),
            self._livelaw.search(query, max_results=livelaw_n),
            self._bb.search(query, max_results=bb_n),
            return_exceptions=True,
        )

        # Collect non-error results
        combined: list[KanoonResult] = []
        source_counts: dict[str, int] = {}
        for source_name, batch in [
            ("kanoon_scraper", kanoon_res),
            ("sc_website", sc_res),
            ("livelaw_rss", ll_res),
            ("bb_rss", bb_res),
        ]:
            if isinstance(batch, Exception):
                logger.warning(f"[FreeLegalClient] {source_name} raised: {batch}")
                continue
            if isinstance(batch, list):
                combined.extend(batch)
                source_counts[source_name] = len(batch)

        logger.info(f"[FreeLegalClient] Raw counts: {source_counts}")

        # Year filter (best-effort: filter by date string)
        if from_year or to_year:
            combined = self._filter_by_year(combined, from_year, to_year)

        # Deduplicate by title hash
        seen: set[str] = set()
        deduped: list[KanoonResult] = []
        for r in combined:
            key = _content_hash(r.title)
            if key not in seen:
                seen.add(key)
                deduped.append(r)

        # Sort: SC court first, then by relevance_score descending
        def _sort_key(r: KanoonResult) -> tuple[float, float]:
            authority_bonus = 0.10 if "Supreme Court" in r.court else 0.0
            return (r.relevance_score + authority_bonus, 0)

        deduped.sort(key=_sort_key, reverse=True)

        final = deduped[:max_results]
        logger.info(
            f"[FreeLegalClient] '{query[:60]}' → {len(final)} merged results "
            f"(from {len(combined)} raw, {len(combined) - len(deduped)} duplicates removed)"
        )
        return final

    async def get_document(self, doc_id: str) -> Optional[KanoonResult]:
        """Fetch full text from Indian Kanoon by constructing doc URL."""
        url = f"https://indiankanoon.org/doc/{doc_id}/"
        full_text = await self._kanoon.get_full_text(url)
        if not full_text:
            return None
        return KanoonResult(
            doc_id=doc_id,
            title=f"Document {doc_id}",
            court="",
            date="",
            headline=full_text[:500],
            url=url,
            full_text=full_text,
            relevance_score=1.0,
        )

    async def search_section(self, act_name: str, section: str) -> list[KanoonResult]:
        """Convenience: search cases interpreting a specific section."""
        query = f'"{act_name}" "{section}"'
        return await self.search(query, max_results=10)

    async def get_act_context(self, query: str) -> dict:
        """
        Fetch eCourts NJDG statistics for the act/section in the query.
        Returns a supplementary stats dict (can be injected into research context).
        """
        return await self._ecourts.get_act_stats(query)

    # ── Internal helpers ────────────────────────────────────────────────────

    @staticmethod
    def _filter_by_year(
        results: list[KanoonResult],
        from_year: Optional[int],
        to_year: Optional[int],
    ) -> list[KanoonResult]:
        """Best-effort year filter: keeps results with unreadable dates."""
        filtered: list[KanoonResult] = []
        for r in results:
            year = _extract_year(r.date)
            if year is None:
                filtered.append(r)  # keep uncertain dates
                continue
            if from_year and year < from_year:
                continue
            if to_year and year > to_year:
                continue
            filtered.append(r)
        return filtered


def _extract_year(date_str: str) -> Optional[int]:
    """Extract 4-digit year from any date string format."""
    m = re.search(r"\b(19|20)\d{2}\b", date_str)
    return int(m.group()) if m else None


# ══════════════════════════════════════════════════════════════════════════════
#  Module-level singleton
# ══════════════════════════════════════════════════════════════════════════════

_free_client: Optional[FreeLegalClient] = None


def get_free_legal_client() -> FreeLegalClient:
    """Return the global FreeLegalClient singleton."""
    global _free_client
    if _free_client is None:
        _free_client = FreeLegalClient()
    return _free_client
