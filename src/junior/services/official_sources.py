"""Curated official sources + study materials for Indian legal research.

This is intentionally static and offline-friendly: we return metadata (title/url/etc)
that the UI can render and the user can open in the browser.

We keep the shape compatible with the frontend ResearchPanel (id/title/type/summary/source).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Iterable, Optional
import json
import re
from cachetools import TTLCache
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from junior.core import get_logger, settings

logger = get_logger(__name__)

# In-memory cache for search results (100 queries, 1 hour TTL)
SEARCH_CACHE = TTLCache(maxsize=100, ttl=3600)

# Try to import DDGS, but don't crash if it fails
try:
    from ddgs import DDGS
    HAS_DDGS = True
except ImportError:
    logger.warning("ddgs not installed. Live search disabled.")
    HAS_DDGS = False

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

# Define trusted domains for live search
TRUSTED_DOMAINS = [
    # Government / Official
    "indiacode.nic.in",
    "egazette.nic.in",
    "sci.gov.in",
    "ecourts.gov.in",
    "legislative.gov.in",
    "bombayhighcourt.nic.in",
    "delhihighcourt.nic.in",
    "hc.ap.nic.in",
    "karnatakajudiciary.kar.nic.in",
    "hcmadras.tn.nic.in",
    "allahabadhighcourt.in",
    
    # Legal Databases (Case Law)
    "indiankanoon.org",
    "casemine.com",
    "manupatra.com",
    "scconline.com",
    "legalcrystal.com",
    
    # Legal News & Analysis
    "livelaw.in",
    "barandbench.com",
    "legalserviceindia.com",
    "blog.ipleaders.in",
    "mondaq.com",
    "pathlegal.in",
    "lawrato.com",
    "vakilno1.com"
]

async def expand_query(user_query: str, category: Optional[str] = None) -> list[str]:
    """
    Uses LLM to generate specific search queries from a broad user intent.
    Optimized for speed using a smaller model and async execution.
    """
    # If query is very specific (looks like a citation), don't expand
    if any(x in user_query.lower() for x in [" v. ", " vs ", "air ", "scc ", "scr "]):
        return [user_query]

    if not settings.groq_api_key:
        return [f"{user_query} India law"]

    try:
        # Use a faster model for query expansion
        llm = ChatGroq(
            model="llama-3.1-8b-instant", # Faster than default
            temperature=0.2,
            api_key=settings.groq_api_key
        )
        
        category_instruction = ""
        if category:
            if category.lower() == "precedent":
                category_instruction = "Focus ONLY on finding case law, judgments, and citations."
            elif category.lower() == "act":
                category_instruction = "Focus ONLY on finding Acts, Sections, and Statutes."
            elif category.lower() == "study":
                category_instruction = "Focus on legal analysis, articles, and commentaries."

        prompt = f"""You are an expert legal search assistant. 
        Convert the user's query into 2-3 specific, effective search queries for finding Indian laws.
        
        User Query: "{user_query}"
        Context: {category_instruction}
        
        Rules:
        1. Return ONLY a JSON list of strings.
        2. Keep queries short and keyword-heavy.
        
        Example Output:
        ["IPC Section 390 robbery", "Supreme Court judgment robbery"]
        """
        
        response = await llm.ainvoke([
            SystemMessage(content="Output JSON only."),
            HumanMessage(content=prompt)
        ])
        
        content = response.content.strip()
        if "```" in content:
            content = content.split("```")[1].replace("json", "").strip()
            
        queries = json.loads(content)
        if isinstance(queries, list):
            if not queries:
                return [f"{user_query} India law"]
            return queries[:3] 
            
    except Exception as e:
        logger.error(f"Query expansion failed: {e}")
        
    return [f"{user_query} India law"]

async def search_live(query: str, category: Optional[str] = None, limit: int = 10) -> list[OfficialSource]:
    """
    Perform a live web search restricted to trusted legal domains.
    Uses parallel execution for speed + Caching.
    """
    if not HAS_DDGS:
        return []

    # Check Cache
    cache_key = f"{query}::{category}::{limit}"
    if cache_key in SEARCH_CACHE:
        logger.info(f"Serving cached results for: {query}")
        return SEARCH_CACHE[cache_key]

    # 1. Determine Search Strategy based on Category
    base_queries = [query]
    
    # If category is specific, we might not need expansion, or we expand differently
    # But let's run expansion in parallel with a direct search
    
    tasks = [expand_query(query, category)]
    
    # Execute expansion
    expanded_results = await asyncio.gather(*tasks)
    search_queries = expanded_results[0]
    
    # Add the original query if not present, but optimized for the category
    if category:
        if category.lower() == "precedent":
             search_queries.append(f"{query} judgment Supreme Court India")
        elif category.lower() == "act":
             search_queries.append(f"{query} Act India code")
    
    # Deduplicate queries
    search_queries = list(set(search_queries))
    logger.info(f"Searching for: {search_queries} (Category: {category})")

    all_results = []
    seen_urls = set()
    
    async def run_single_search(q: str):
        local_results = []
        try:
            # Construct the actual query string for DDG
            # We can use site: operators here based on category for the "Direct" search
            # but DDG sometimes fails with too many operators.
            # Let's stick to keyword boosting + post-filtering, but maybe add one "site:" query
            
            full_query = q
            if "india" not in q.lower():
                full_query += " India"
            
            # Category specific boosting
            if category:
                if category.lower() == "precedent" and "judgment" not in full_query.lower():
                    full_query += " judgment"
                elif category.lower() == "act" and "act" not in full_query.lower():
                    full_query += " act"

            # Run synchronous DDGS in a thread to avoid blocking the event loop
            def _do_search():
                with DDGS() as ddgs:
                    return list(ddgs.text(full_query, region="in-en", max_results=10))
            
            search_results = await asyncio.to_thread(_do_search)
            
            for res in search_results:
                url = res.get('href', '')
                if url in seen_urls: continue
                
                # Domain Filter
                matched_domain = False
                for domain in TRUSTED_DOMAINS:
                    if domain in url:
                        matched_domain = True
                        break
                
                # Category Strictness
                # If user asked for "Official", strictly enforce .gov.in / .nic.in
                if category and category.lower() == "official":
                    if not any(d in url for d in ["gov.in", "nic.in", "sci.gov.in"]):
                        matched_domain = False

                if not matched_domain: continue

                seen_urls.add(url)
                
                # Determine type
                doc_type = "Official"
                title_lower = res['title'].lower()
                if "judgment" in title_lower or "vs" in title_lower or "court" in title_lower:
                    doc_type = "Precedent"
                elif "act" in title_lower or "section" in title_lower or "code" in title_lower:
                    doc_type = "Act"
                
                # Determine authority
                authority = "official"
                if any(x in url for x in ["livelaw", "barandbench", "indiankanoon", "legalservice", "ipleaders"]):
                    authority = "study"

                local_results.append(OfficialSource(
                    id=f"live_{abs(hash(url))}",
                    title=res['title'],
                    type=doc_type,
                    summary=res['body'],
                    source=url.split('/')[2],
                    url=url,
                    publisher="Web Search",
                    authority=authority,
                    tags=("live_search",)
                ))
        except Exception as e:
            logger.warning(f"Search failed for '{q}': {e}")
        return local_results

    # Run all searches in parallel
    search_tasks = [run_single_search(q) for q in search_queries]
    results_lists = await asyncio.gather(*search_tasks)
    
    for r_list in results_lists:
        all_results.extend(r_list)

    final_results = all_results[:limit]
    
    # Cache the results
    SEARCH_CACHE[cache_key] = final_results
    
    return final_results


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

def get_preview(url: str) -> dict:
    """
    Fetches and extracts main content from a URL for instant preview.
    Uses trafilatura for robust extraction.
    """
    try:
        import trafilatura
        
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return {"error": "Could not fetch URL"}
            
        text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
        if not text:
            return {"error": "Could not extract text"}
            
        # Basic summarization (first 1000 chars)
        summary = text[:1000] + "..." if len(text) > 1000 else text
        
        return {
            "title": trafilatura.extract(downloaded, only_with_metadata=True).get('title', 'Preview'),
            "content": summary,
            "full_text_length": len(text)
        }
    except Exception as e:
        logger.error(f"Preview failed for {url}: {e}")
        return {"error": str(e)}


async def search_sources(
    query: str = "",
    *,
    category: Optional[str] = None,
    authority: Optional[str] = None,
    limit: int = 25,
) -> list[OfficialSource]:
    """Search the curated sources catalog AND live web."""
    
    # 1. Search static catalog
    catalog_results = []
    for item in CATALOG:
        # Filter by category if provided
        if category and category.lower() != "all":
            if item.type.lower() != category.lower():
                continue

        # Filter by authority if provided
        if authority:
            if item.authority.lower() != authority.lower():
                continue

        # Filter by text query
        if _matches_query(item, query):
            catalog_results.append(item)

    # 2. If query is present, perform live search
    live_results = []
    if query and len(query) > 3:
        try:
            live_results = await search_live(query, category=category, limit=limit)
            
            # Apply post-search filters to live results
            if category and category.lower() != "all":
                live_results = [r for r in live_results if r.type.lower() == category.lower()]
            if authority:
                live_results = [r for r in live_results if r.authority.lower() == authority.lower()]
                
        except Exception as e:
            logger.error(f"Error in live search integration: {e}")

    # 3. Combine results (Live first if query exists, else Catalog)
    combined = live_results + catalog_results
    
    # Deduplicate by URL
    seen_urls = set()
    unique_results = []
    for item in combined:
        if item.url not in seen_urls:
            unique_results.append(item)
            seen_urls.add(item.url)

    return unique_results[:limit]


