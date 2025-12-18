"""Curated official sources + study materials for Indian legal research.

This is intentionally static and offline-friendly: we return metadata (title/url/etc)
that the UI can render and the user can open in the browser.

We keep the shape compatible with the frontend ResearchPanel (id/title/type/summary/source).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

@dataclass(frozen=True)
class OfficialSource:
    id: str
    title: str
    type: str  # Official | Study | Act | Constitution | Precedent | Law
    summary: str
    source: str
    url: str
    publisher: str
    authority: str  # official | study
    tags: tuple[str, ...] = ()

# NOTE: Keep this list focused and genuinely official.
# Avoid third-party aggregators.
CATALOG: tuple[OfficialSource, ...] = (
    OfficialSource(
        id="os_india_code",
        title="India Code (Legislative Department)",
        type="Official",
        summary="Official repository of Central Acts, Rules, Regulations, and Orders.",
        source="Government of India",
        url="https://www.indiacode.nic.in/",
        publisher="Legislative Department, Ministry of Law and Justice",
        authority="official",
        tags=("acts", "rules", "central", "bare-act", "criminal", "civil"),
    ),
    OfficialSource(
        id="os_egazette",
        title="e-Gazette of India",
        type="Official",
        summary="Official Gazette publications and notifications.",
        source="Government of India",
        url="https://egazette.nic.in/",
        publisher="Department of Publication",
        authority="official",
        tags=("gazette", "notifications"),
    ),
    OfficialSource(
        id="os_sci_judgments",
        title="Supreme Court of India — Judgments",
        type="Official",
        summary="Supreme Court judgments and orders (official portal).",
        source="Supreme Court of India",
        url="https://main.sci.gov.in/judgments",
        publisher="Supreme Court of India",
        authority="official",
        tags=("case-law", "supreme-court", "criminal", "civil"),
    ),
    OfficialSource(
        id="os_sci_causes",
        title="Supreme Court of India — Cause List",
        type="Official",
        summary="Daily/weekly cause lists and listings.",
        source="Supreme Court of India",
        url="https://main.sci.gov.in/",
        publisher="Supreme Court of India",
        authority="official",
        tags=("cause-list", "listing"),
    ),
    OfficialSource(
        id="os_ecourts",
        title="eCourts Services",
        type="Official",
        summary="Case status, orders, and cause lists across district/subordinate courts.",
        source="eCourts",
        url="https://ecourts.gov.in/",
        publisher="eCommittee, Supreme Court of India",
        authority="official",
        tags=("district-courts", "case-status", "criminal", "civil"),
    ),
    OfficialSource(
        id="os_ecourts_efiling",
        title="eCourts — eFiling",
        type="Official",
        summary="Official eFiling portal for participating courts.",
        source="eCourts",
        url="https://efiling.ecourts.gov.in/",
        publisher="eCommittee, Supreme Court of India",
        authority="official",
        tags=("efiling", "procedure", "civil", "criminal"),
    ),
    OfficialSource(
        id="os_njdg",
        title="National Judicial Data Grid (NJDG)",
        type="Official",
        summary="Official dashboards and statistics for Indian judiciary.",
        source="NJDG",
        url="https://njdg.ecourts.gov.in/",
        publisher="eCommittee, Supreme Court of India",
        authority="official",
        tags=("statistics", "dashboards"),
    ),
    OfficialSource(
        id="os_doj",
        title="Department of Justice",
        type="Official",
        summary="Policies, schemes, and administrative updates for justice delivery.",
        source="Government of India",
        url="https://doj.gov.in/",
        publisher="Department of Justice, Ministry of Law and Justice",
        authority="official",
        tags=("policy", "schemes", "criminal", "civil"),
    ),
    OfficialSource(
        id="os_law_commission",
        title="Law Commission of India — Reports",
        type="Official",
        summary="Law Commission reports and consultation papers.",
        source="Government of India",
        url="https://lawcommissionofindia.nic.in/",
        publisher="Law Commission of India",
        authority="official",
        tags=("reports", "reform", "criminal", "civil"),
    ),

    # High Courts (official portals)
    OfficialSource(
        id="os_delhi_hc",
        title="Delhi High Court — Official Portal",
        type="Official",
        summary="High Court portal for cause lists, judgments, orders, and notices.",
        source="Delhi High Court",
        url="https://delhihighcourt.nic.in/",
        publisher="Delhi High Court",
        authority="official",
        tags=("high-court", "delhi", "civil", "criminal"),
    ),
    OfficialSource(
        id="os_bombay_hc",
        title="Bombay High Court — Official Portal",
        type="Official",
        summary="High Court portal for judgments, cause lists, and court information.",
        source="Bombay High Court",
        url="https://bombayhighcourt.nic.in/",
        publisher="Bombay High Court",
        authority="official",
        tags=("high-court", "bombay", "civil", "criminal"),
    ),
    OfficialSource(
        id="os_madras_hc",
        title="Madras High Court — Official Portal",
        type="Official",
        summary="High Court portal for judgments, cause lists, and notices.",
        source="Madras High Court",
        url="https://www.hcmadras.tn.nic.in/",
        publisher="Madras High Court",
        authority="official",
        tags=("high-court", "madras", "civil", "criminal"),
    ),
    OfficialSource(
        id="os_calcutta_hc",
        title="Calcutta High Court — Official Portal",
        type="Official",
        summary="High Court portal for judgments, cause lists, and court information.",
        source="Calcutta High Court",
        url="https://www.calcuttahighcourt.gov.in/",
        publisher="Calcutta High Court",
        authority="official",
        tags=("high-court", "calcutta", "civil", "criminal"),
    ),

    # Legal Aid (official)
    OfficialSource(
        id="os_nalsa",
        title="NALSA (National Legal Services Authority)",
        type="Official",
        summary="Legal aid schemes, SOPs, and public guidance (official).",
        source="NALSA",
        url="https://nalsa.gov.in/",
        publisher="National Legal Services Authority",
        authority="official",
        tags=("legal-aid", "procedure", "criminal", "civil"),
    ),

    # Official PDFs / manuals (direct ingestion candidates)
    OfficialSource(
        id="os_practice_pdf_waas",
        title="Practice Manual / Directions (PDF)",
        type="Official",
        summary="Public PDF manual (government-hosted). Suitable for RAG ingestion.",
        source="Government of India (S3WaaS hosting)",
        url="https://cdnbbsr.s3waas.gov.in/s3ec0490f1f4972d133619a60c30f3559e/documents/misc/practice.pdf_0.pdf",
        publisher="Government of India",
        authority="official",
        tags=("manual", "practice", "procedure", "pdf"),
    ),

    # Court rules/manuals (usually web pages with PDFs inside)
    OfficialSource(
        id="os_bombay_hc_rules_manuals",
        title="Bombay High Court — Rules & Manuals",
        type="Official",
        summary="Official High Court rules/manuals page (may contain downloadable PDFs).",
        source="Bombay High Court",
        url="https://bombayhighcourt.gov.in/Rules%20&%20Manuals",
        publisher="Bombay High Court",
        authority="official",
        tags=("high-court", "bombay", "rules", "manual", "procedure"),
    ),

    # Glossary (official, web)
    OfficialSource(
        id="os_legislative_glossary",
        title="Legislative Department — Legal Glossary",
        type="Official",
        summary="Official legal glossary by the Legislative Department (web).",
        source="Government of India",
        url="https://legislative.gov.in/legal-glossary/",
        publisher="Legislative Department, Ministry of Law and Justice",
        authority="official",
        tags=("glossary", "definitions", "acts", "drafting"),
    ),

    # Study (official-origin learning material)
    OfficialSource(
        id="st_ecourts_training",
        title="eCourts — User Manuals / Help",
        type="Study",
        summary="Official user manuals and help resources for eCourts services.",
        source="eCourts",
        url="https://ecourts.gov.in/ecourts_home/",
        publisher="eCommittee, Supreme Court of India",
        authority="study",
        tags=("manual", "how-to", "criminal", "civil"),
    ),
    OfficialSource(
        id="st_ecourts_efiling_manuals",
        title="eCourts — eFiling User Guides",
        type="Study",
        summary="Public user guides for eFiling workflows (official).",
        source="eCourts",
        url="https://efiling.ecourts.gov.in/",
        publisher="eCommittee, Supreme Court of India",
        authority="study",
        tags=("manual", "efiling", "procedure", "civil", "criminal"),
    ),
)

def _matches_query(item: OfficialSource, query: str) -> bool:
    q = query.strip().lower()
    if not q:
        return True

    hay = " ".join(
        [
            item.title,
            item.summary,
            item.source,
            item.publisher,
            item.url,
            " ".join(item.tags),
        ]
    ).lower()
    return q in hay

def get_source_by_id(source_id: str) -> Optional[OfficialSource]:
    """Lookup a curated source by id."""
    sid = (source_id or "").strip()
    if not sid:
        return None
    for item in CATALOG:
        if item.id == sid:
            return item
    return None

def search_sources(
    query: str = "",
    *,
    category: Optional[str] = None,
    authority: Optional[str] = None,
    limit: int = 25,
) -> list[OfficialSource]:
    """Search the curated sources catalog.

    Args:
        query: Free-text query.
        category: Optional type filter (Official/Study/Act/etc).
        authority: Optional authority filter (official/study).
        limit: Max items.

    Returns:
        List of matching sources.
    """

    cat = (category or "").strip()
    auth = (authority or "").strip().lower()

    def _ok(it: OfficialSource) -> bool:
        if cat and it.type.lower() != cat.lower():
            return False
        if auth and it.authority.lower() != auth:
            return False
        return _matches_query(it, query)

    items = [it for it in CATALOG if _ok(it)]

    # Sort: official first, then alphabetical.
    def _rank(it: OfficialSource) -> tuple[int, str]:
        return (0 if it.authority == "official" else 1, it.title.lower())

    items.sort(key=_rank)
    return items[: max(1, int(limit or 25))]
