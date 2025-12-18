"""
Researcher Agent - Finds and extracts relevant legal information
"""

import json
import re
from typing import Any, Optional, cast

from junior.core.types import AgentRole, Citation, Court, CaseStatus
from .base import BaseAgent, AgentState

def _as_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, str)) and str(value).strip():
            return int(value)
        return None
    except Exception:
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
        return """You are an expert Indian legal researcher with deep knowledge of Indian case law, statutes, and legal principles. Your role is to:

1. UNDERSTAND the legal query and identify the key legal issues
2. ANALYZE the provided documents and extract relevant information
3. CITE with precision - always reference specific paragraphs and pages
4. CATEGORIZE findings by legal principle or issue
5. NOTE any conflicting precedents or distinctions

CRITICAL RULES:
- NEVER make up case names or citations
- ALWAYS cite the specific paragraph number when referencing a point of law
- DISTINGUISH between ratio decidendi (binding) and obiter dicta (persuasive)
- IDENTIFY the hierarchy of courts (Supreme Court > High Court > District Court)
- FLAG any cases that may have been overruled or distinguished

OUTPUT FORMAT:
For each relevant finding, provide:
- Case Reference: [Case Name] ([Year]) [Court]
- Paragraph: [Number]
- Legal Principle: [Brief statement]
- Relevance: [How it applies to the query]
- Status: [Good Law / Distinguished / Overruled]

Be thorough but concise. Quality over quantity."""

    async def process(self, state: AgentState) -> AgentState:
        """
        Process the research query and find relevant case law

        Args:
            state: Current workflow state with query and documents

        Returns:
            Updated state with research notes and citations
        """
        self.logger.info(f"Researching query: {state.query[:100]}...")

        # Build the research prompt
        prompt = self._build_research_prompt(state)

        # Get LLM response
        response = await self.invoke_llm(prompt)

        # Parse the response to extract citations and notes
        research_notes, citations = self._parse_research_response(response, state.documents)

        # Update state
        state.research_notes.extend(research_notes)
        state.citations.extend(citations)
        state.iteration += 1

        self.logger.info(f"Found {len(citations)} citations, {len(research_notes)} research notes")

        return state

    def _build_research_prompt(self, state: AgentState) -> str:
        """Build the prompt for legal research"""
        documents_text = self.format_documents_for_prompt(state.documents)

        # Only allow citations that reference one of these ids
        allowed_doc_ids = [
            str(d.get("id")) for d in state.documents if d.get("id") is not None
        ]
        allowed_document_ids = [
            str(d.get("document_id")) for d in state.documents if d.get("document_id") is not None
        ]

        prompt = f"""LEGAL RESEARCH QUERY:
{state.query}

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
