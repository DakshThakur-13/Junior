"""
Researcher Agent - Finds and extracts relevant legal information
"""

import json
import re
from typing import Any, Optional, cast

from junior.core import get_logger
from junior.core.types import AgentRole, Citation, Court, CaseStatus
from .base import BaseAgent, AgentState

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Indian Legal Abbreviation Expansion
# Expands shorthand before search so BM25 + embeddings match more documents
# ---------------------------------------------------------------------------
LEGAL_ABBREVIATIONS: dict[str, str] = {
    # Statutes
    "IPC": "Indian Penal Code",
    "CrPC": "Code of Criminal Procedure",
    "CPC": "Code of Civil Procedure",
    "IEA": "Indian Evidence Act",
    "CRPC": "Code of Criminal Procedure",
    "IT Act": "Information Technology Act",
    "NDPS": "Narcotic Drugs and Psychotropic Substances Act",
    "POCSO": "Protection of Children from Sexual Offences Act",
    "SC/ST Act": "Scheduled Castes and Scheduled Tribes Prevention of Atrocities Act",
    "PMLA": "Prevention of Money Laundering Act",
    "RTI": "Right to Information Act",
    "MV Act": "Motor Vehicles Act",
    "GST": "Goods and Services Tax",
    "TDS": "Tax Deducted at Source",
    # Courts
    "SC": "Supreme Court",
    "HC": "High Court",
    "DC": "District Court",
    "SAT": "Securities Appellate Tribunal",
    "NCLAT": "National Company Law Appellate Tribunal",
    "NCLT": "National Company Law Tribunal",
    "NGT": "National Green Tribunal",
    # Petition types
    "SLP": "Special Leave Petition",
    "WP": "Writ Petition",
    "PIL": "Public Interest Litigation",
    "FIR": "First Information Report",
    "Sec.": "Section",
    "Sec ": "Section ",
    "Art.": "Article",
    # Procedural
    "HC order": "High Court order",
    "SC judgment": "Supreme Court judgment",
    "bail": "bail application",
    "anticipatory bail": "anticipatory bail under Section 438 CrPC",
}


def _expand_legal_query(query: str) -> str:
    """Expand Indian legal abbreviations in a query for better retrieval.

    Replaces known shorthands (e.g. IPC → Indian Penal Code) so that
    BM25 keyword search finds more relevant chunks.
    """
    expanded = query
    for abbr, full in LEGAL_ABBREVIATIONS.items():
        # Replace whole-word occurrences, case-insensitive
        pattern = re.compile(r'\b' + re.escape(abbr) + r'\b')
        expanded = pattern.sub(full, expanded)
    return expanded


def _as_int(value: Any) -> Optional[int]:
    """Convert value to int with proper error logging.
    
    Args:
        value: Value to convert to integer
        
    Returns:
        Integer value or None if conversion fails
        
    Logs:
        Warning if conversion fails with non-empty value
    """
    try:
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, str)) and str(value).strip():
            return int(value)
        return None
    except (ValueError, TypeError) as e:
        # Log the error so silent failures are visible
        logger.warning(f"Failed to convert value to int: {value!r} - {e}")
        return None
    except Exception as e:
        # Catch unexpected errors and log them
        logger.error(f"Unexpected error converting value to int: {value!r} - {e}", exc_info=True)
        return None

class ResearcherAgent(BaseAgent):
    """
    The Researcher Agent is responsible for:
    1. Understanding the legal query
    2. Searching the case law database
    3. Extracting relevant excerpts with pinpoint citations
    4. Identifying the legal principles at play
    """

    role = AgentRole.RESEARCHER

    @property
    def system_prompt(self) -> str:
        return """You are a Senior Advocate with 30 years of experience before the Supreme Court of India and all High Courts. You combine encyclopaedic knowledge of Indian case law with razor-sharp analytical precision.

INDIAN COURT HIERARCHY (binding precedent flows downward):
  [1] Supreme Court of India  →  Binding on ALL courts in India (Art. 141)
  [2] High Courts             →  Binding within their territorial jurisdiction
  [3] District / Sessions Courts  →  Trial-level, limited precedential value
  [4] Tribunals (NCLAT, NGT, SAT, ITAT, DRAT)  →  Persuasive only
  [5] Foreign / Privy Council  →  Highly persuasive, not binding

FOUNDATIONAL LANDMARK CASES YOU MUST KNOW:
  Constitutional:
    Kesavananda Bharati v. State of Kerala (1973) 4 SCC 225  – Basic Structure Doctrine
    Maneka Gandhi v. Union of India (1978) 1 SCC 248         – Art.21 expanded; due process
    Minerva Mills v. Union of India (1980) 3 SCC 625         – Balance between rights & DPSPs
    I.R. Coelho v. State of Tamil Nadu (2007) 2 SCC 1        – 9th Schedule judicial review
    Navtej Singh Johar v. Union of India (2018) 10 SCC 1     – Decriminalisation of S.377 IPC
    Joseph Shine v. Union of India (2018) 2 SCC 189          – Adultery law struck down
  Criminal:
    Bachan Singh v. State of Punjab (1980) 2 SCC 684         – Rarest of rare doctrine capital punishment
    Arnesh Kumar v. State of Bihar (2014) 8 SCC 273          – Arrest guidelines S.498A IPC
    Lalita Kumari v. Govt. of UP (2014) 2 SCC 1              – Mandatory FIR registration
    Satender Kumar Antil v. CBI (2022) 10 SCC 51             – Bail jurisprudence post-BNSS
  Civil / Property:
    Sarla Mudgal v. Union of India (1995) 3 SCC 635          – Bigamy and conversion
    Vineeta Sharma v. Rakesh Sharma (2020) 9 SCC 1           – Hindu daughters coparcenary rights
  Service / Constitutional Remedies:
    Vishaka v. State of Rajasthan (1997) 6 SCC 241           – Workplace sexual harassment
    Indra Sawhney v. Union of India (1992) 3 SCC 217         – OBC reservations 50% cap
    M. Nagaraj v. Union of India (2006) 8 SCC 212            – SC/ST reservation in promotions

REFERENCING RULES:
- Supreme Court reporters: SCC (preferred), AIR SC, SCR, SCALE
- High Court reporters: State-specific (e.g., Bom LR, Mad LJ, Del HC)
- Always cite: Case Name (Year) Volume Reporter Page at Para X

RESEARCH METHODOLOGY:
1. IDENTIFY key legal issues under Indian statutory/constitutional framework
2. FIND binding Supreme Court authority first, then HC judgments
3. DISTINGUISH ratio decidendi from obiter dicta explicitly
4. NOTE if a case has been affirmed, overruled, or distinguished by later SC bench
5. ASSESS jurisdictional relevance (e.g., HC judgment applies only in that state)
6. EXTRACT the exact paragraph number for every proposition

CRITICAL RULES:
- NEVER invent case names, citations, or paragraph numbers
- Flag any case decided by a smaller bench if a larger bench has spoken
- Note Constitution Bench (5+ judges) authority as highest within SC hierarchy
- Identify if relevant legislation has been amended post the cited judgment

OUTPUT FORMAT:
For each relevant finding:
- Case Reference: [Name] (Year) Volume Reporter Page
- Court & Bench Strength: [e.g., SC – 5-Judge Constitution Bench]
- Paragraph: [Number]
- Legal Principle: [Precise statement]
- Relevance to Query: [Direct application]
- Binding/Persuasive: [Binding / Persuasive / Obiter]
- Current Status: [Good Law / Distinguished by X / Overruled by Y]

Quality and accuracy over quantity. A single verified citation beats ten doubtful ones."""

    async def process(self, state: AgentState) -> AgentState:
        """
        Process the research query and find relevant case law.

        Enhancements:
        - Expands Indian legal abbreviations before search
        - Addresses specific issues raised by the Critic in previous iterations
        - Reformulates the query (up to 2 times) when 0 documents are retrieved
        """
        # 1. Expand abbreviations for better retrieval
        if not state.expanded_query:
            state.expanded_query = _expand_legal_query(state.query)
            if state.expanded_query != state.query:
                self.logger.info(f"Query expanded: '{state.query[:60]}' -> '{state.expanded_query[:60]}'")

        effective_query = state.expanded_query or state.query
        self.logger.info(f"Researching query: {effective_query[:100]}...")

        # 2. If Critic raised specific issues, do a targeted re-search pass
        if state.critic_issues and state.iteration > 0:
            self.logger.info(f"Targeted re-search for {len(state.critic_issues)} critic issues")
            prompt = self._build_targeted_research_prompt(state)
        else:
            prompt = self._build_research_prompt(state)

        # Get LLM response
        response = await self.invoke_llm(prompt)

        # Parse the response to extract citations and notes
        research_notes, citations = self._parse_research_response(response, state.documents)

        # 3. If we found nothing and haven't exhausted reformulation attempts, try rephrasing
        if not citations and not research_notes and state.reformulation_attempts < 2:
            state.reformulation_attempts += 1
            self.logger.warning(
                f"No results found. Reformulating query (attempt {state.reformulation_attempts}/2)..."
            )
            reformulated = await self._reformulate_query(state.query)
            if reformulated and reformulated != state.query:
                state.expanded_query = reformulated
                prompt = self._build_research_prompt(state)
                response = await self.invoke_llm(prompt)
                research_notes, citations = self._parse_research_response(response, state.documents)

        # Update state
        state.research_notes.extend(research_notes)
        state.citations.extend(citations)
        state.iteration += 1

        self.logger.info(f"Found {len(citations)} citations, {len(research_notes)} research notes")

        return state

    async def _reformulate_query(self, query: str) -> str:
        """Ask the LLM to rephrase the query with different legal keywords.

        Used when the original (and expanded) query returns no documents.
        """
        prompt = (
            f"You are an Indian legal research assistant.\n"
            f"The following query returned no results in our legal database:\n\n"
            f"ORIGINAL QUERY: {query}\n\n"
            f"Rephrase it using alternative Indian legal terminology, section numbers, "
            f"or case law keywords. Return ONLY the rephrased query — no explanation."
        )
        try:
            return (await self.invoke_llm(prompt)).strip()
        except Exception as e:
            self.logger.warning(f"Query reformulation failed: {e}")
            return query

    def _build_targeted_research_prompt(self, state: AgentState) -> str:
        """Build a focused prompt to address specific weaknesses flagged by the Critic."""
        issues_text = "\n".join(f"  - {issue}" for issue in state.critic_issues)
        documents_text = self.format_documents_for_prompt(state.documents)

        return f"""TARGETED LEGAL RE-SEARCH

ORIGINAL QUERY:
{state.query}

CRITIC HAS IDENTIFIED THESE SPECIFIC WEAKNESSES:
{issues_text}

AVAILABLE DOCUMENTS:
{documents_text}

TASK:
Focus ONLY on finding evidence in the documents that directly addresses the gaps
and weaknesses listed above. For each issue, find:
1. A specific paragraph or passage that resolves it
2. The strongest applicable precedent
3. Any statutory provision that supports the position

Return findings in the same JSON format as standard research."""

    def _build_research_prompt(self, state: AgentState) -> str:
        """Build the prompt for legal research"""
        # Use expanded query for the prompt if available
        effective_query = state.expanded_query or state.query
        documents_text = self.format_documents_for_prompt(state.documents)

        # Only allow citations that reference one of these ids
        allowed_doc_ids = [
            str(d.get("id")) for d in state.documents if d.get("id") is not None
        ]
        allowed_document_ids = [
            str(d.get("document_id")) for d in state.documents if d.get("document_id") is not None
        ]

        prompt = f"""LEGAL RESEARCH QUERY:
{effective_query}

AVAILABLE DOCUMENTS:
{documents_text}

PREVIOUS RESEARCH NOTES:
{chr(10).join(state.research_notes) if state.research_notes else 'None - this is the first research pass.'}

TASK:
1. Analyze the documents above in relation to the legal query
2. Extract ALL relevant legal principles with pinpoint citations
3. Note any conflicts or distinctions between cases
4. Identify the strongest precedents for and against the query position
5. Summarize the current state of law on this issue

Provide your research findings in a structured format."""

        prompt += f"""

STRICT OUTPUT REQUIREMENTS:
- Return ONLY valid JSON. No markdown, no extra text.
- You MUST NOT invent case names/citations.
- Only cite from AVAILABLE DOCUMENTS. If there are no documents, return an empty citations list.
- Every citation must reference a real document using `source_document_ref` equal to one of these values:
    - ids: {allowed_doc_ids}
    - document_ids: {allowed_document_ids}

JSON SCHEMA:
{{
    "research_notes": [string],
    "citations": [
        {{
            "source_document_ref": string,
            "case_name": string,
            "case_number": string,
            "court": "supreme_court"|"high_court"|"district_court"|"tribunal"|"other",
            "year": number,
            "paragraph": number|null,
            "status": "good_law"|"distinguished"|"overruled",
            "principle": string,
            "relevance": string
        }}
    ]
}}
"""

        return prompt

    def _parse_research_response(
        self,
        response: str,
        documents: list[dict],
    ) -> tuple[list[str], list[Citation]]:
        """
        Parse LLM response to extract research notes and citations

        Args:
            response: LLM response text
            documents: Original documents for reference

        Returns:
            Tuple of (research_notes, citations)
        """
        # Try JSON first (preferred)
        parsed = self._try_parse_json(response)
        if parsed is not None:
            notes_value = parsed.get("research_notes")
            notes_list: list[Any] = notes_value if isinstance(notes_value, list) else []
            notes = [str(n) for n in notes_list if n is not None]

            citations_value = parsed.get("citations")
            citations_in: list[Any] = citations_value if isinstance(citations_value, list) else []

            citations_out: list[Citation] = []
            for item in citations_in:
                citation = self._citation_from_json_item(item, documents)
                if citation:
                    citations_out.append(citation)

            return notes, citations_out

        # Fallback: legacy parsing, but enforce that we only keep citations that match a provided document.
        research_notes: list[str] = []
        citations: list[Citation] = []

        lines = (response or "").strip().split("\n")
        current_note: list[str] = []

        for line in lines:
            line = line.strip()
            if not line:
                if current_note:
                    research_notes.append("\n".join(current_note))
                    current_note = []
                continue

            if "Case Reference:" in line or "para" in line.lower():
                citation = self._extract_citation_from_line(line, documents)
                if citation:
                    citations.append(citation)
            current_note.append(line)

        if current_note:
            research_notes.append("\n".join(current_note))

        return research_notes, citations

    def _try_parse_json(self, response: str) -> Optional[dict]:
        text = (response or "").strip()
        if not text:
            return None

        try:
            value = json.loads(text)
            return value if isinstance(value, dict) else None
        except Exception:
            pass

        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return None
        try:
            value = json.loads(m.group(0))
            return value if isinstance(value, dict) else None
        except Exception:
            return None

    def _citation_from_json_item(self, item: object, documents: list[dict]) -> Optional[Citation]:
        if not isinstance(item, dict):
            return None

        item_dict = cast(dict[str, Any], item)

        def _as_str(value: Any) -> Optional[str]:
            if isinstance(value, str) and value.strip():
                return value
            return None

        source_ref = item_dict.get("source_document_ref")
        if not isinstance(source_ref, str) or not source_ref.strip():
            return None

        matched_doc = self._match_document_ref(source_ref, documents)
        if matched_doc is None:
            # Enforce "no hallucinated citations": ignore anything that doesn't anchor to provided docs.
            return None

        matched = cast(dict[str, Any], matched_doc)

        case_name = _as_str(item_dict.get("case_name"))
        case_number = _as_str(item_dict.get("case_number"))
        court_str = _as_str(item_dict.get("court")) or "other"

        year_val = item_dict.get("year")
        para_val = item_dict.get("paragraph")

        status_str = _as_str(item_dict.get("status")) or "good_law"

        # Best-effort defaults from the matched document, if available.
        if not case_name:
            case_name = (
                _as_str(matched.get("title"))
                or _as_str(matched.get("case_title"))
                or _as_str(matched.get("document_title"))
                or "Unknown"
            )
        if not case_number:
            case_number = _as_str(matched.get("case_number")) or _as_str(matched.get("document_id")) or "Unknown"

        year = 0
        try:
            if isinstance(year_val, (int, str)) and str(year_val).strip():
                year = int(year_val)
            else:
                doc_year = matched.get("year")
                year = int(doc_year) if isinstance(doc_year, (int, str)) and str(doc_year).strip() else 0
        except Exception:
            year = 0

        paragraph: Optional[int]
        try:
            paragraph = int(para_val) if isinstance(para_val, (int, str)) and str(para_val).strip() else None
        except Exception:
            paragraph = None

        court_key = str(court_str)
        court = {
            "supreme_court": Court.SUPREME_COURT,
            "high_court": Court.HIGH_COURT,
            "district_court": Court.DISTRICT_COURT,
            "tribunal": Court.TRIBUNAL,
            "other": Court.OTHER,
        }.get(court_key, Court.OTHER)

        status_key = str(status_str)
        status = {
            "good_law": CaseStatus.GOOD_LAW,
            "distinguished": CaseStatus.DISTINGUISHED,
            "overruled": CaseStatus.OVERRULED,
        }.get(status_key, CaseStatus.GOOD_LAW)

        return Citation(
            case_name=case_name,
            case_number=case_number,
            court=court,
            year=year,
            paragraph=paragraph,
            status=status,
            source_document_id=str(matched.get("id") or matched.get("document_id") or ""),
            page=_as_int(matched.get("page_number")),
            chunk_id=str(matched.get("id")) if matched.get("id") is not None else None,
            excerpt=str(matched.get("content"))[:500] if matched.get("content") else None,
        )

    def _match_document_ref(self, source_ref: str, documents: list[dict]) -> Optional[dict]:
        ref = source_ref.strip()
        if not ref:
            return None
        for doc in documents:
            if str(doc.get("id")) == ref:
                return doc
            if str(doc.get("document_id")) == ref:
                return doc
        return None

    def _extract_citation_from_line(
        self,
        line: str,
        documents: list[dict],
    ) -> Optional[Citation]:
        """
        Extract a citation from a text line

        This is a simplified extraction - in production, you'd use
        more sophisticated NLP or regex patterns
        """
        import re

        # Only accept citations we can anchor to a provided document

        # Try to find paragraph reference
        para_match = re.search(r'[Pp]ara(?:graph)?[:\s]*(\d+)', line)
        paragraph = int(para_match.group(1)) if para_match else None

        # Determine court from keywords
        court = Court.OTHER
        line_lower = line.lower()
        if "supreme court" in line_lower or "sc" in line_lower:
            court = Court.SUPREME_COURT
        elif "high court" in line_lower or "hc" in line_lower:
            court = Court.HIGH_COURT
        elif "district" in line_lower:
            court = Court.DISTRICT_COURT
        elif "tribunal" in line_lower:
            court = Court.TRIBUNAL

        # Determine status
        status = CaseStatus.GOOD_LAW
        if "overruled" in line_lower:
            status = CaseStatus.OVERRULED
        elif "distinguished" in line_lower:
            status = CaseStatus.DISTINGUISHED

        # Extract case name (simplified - take first quoted text or first part)
        name_match = re.search(r'"([^"]+)"', line)
        if name_match:
            case_name = name_match.group(1)
        else:
            # Take the first meaningful part of the line
            case_name = line.split("(")[0].strip()[:50]

        if not case_name or len(case_name) < 3:
            return None

        matched_doc = None
        for doc in documents:
            title = (doc.get("title") or "")
            content = (doc.get("content") or "")
            if case_name.lower() in title.lower() or case_name.lower() in content.lower():
                matched_doc = doc
                break

        if matched_doc is None:
            return None

        # Try to find year pattern, else fallback to document metadata.
        year_match = re.search(r'\((\d{4})\)', line)
        if year_match:
            year = int(year_match.group(1))
        else:
            try:
                year = int(matched_doc.get("year") or 0)
            except Exception:
                year = 0

        return Citation(
            case_name=case_name,
            case_number=matched_doc.get("case_number") or matched_doc.get("document_id") or "Unknown",
            court=court,
            year=year,
            paragraph=paragraph,
            status=status,
            source_document_id=str(matched_doc.get("id") or matched_doc.get("document_id") or ""),
            page=_as_int(matched_doc.get("page_number")),
            chunk_id=str(matched_doc.get("id")) if matched_doc.get("id") is not None else None,
            excerpt=str(matched_doc.get("content"))[:500] if matched_doc.get("content") else None,
        )
