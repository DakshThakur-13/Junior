"""Legislative Department Legal Glossary Service

Fetches and caches the official legal glossary from legislative.gov.in
for term verification before translation. This ensures accurate legal terminology
is preserved and correctly understood before translation decisions are made.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx

from junior.core import get_logger, settings

logger = get_logger(__name__)

@dataclass
class GlossaryTerm:
    """A legal term from the official glossary"""
    term: str
    definition: str
    category: Optional[str] = None  # e.g., "Constitutional Law", "Criminal Law"
    related_terms: list[str] = field(default_factory=list)

class LegalGlossaryService:
    """
    Service for accessing the Legislative Department's official legal glossary.

    Features:
    - Fetches official glossary on first use
    - Caches locally for offline/fast access
    - Provides term lookups for translation verification
    """

    GLOSSARY_URL = "https://legislative.gov.in/legal-glossary/"
    CACHE_FILE = Path("uploads") / "glossary" / "legislative_glossary.json"

    def __init__(self):
        self._glossary: Optional[dict[str, GlossaryTerm]] = None
        self._cache_loaded = False

    async def initialize(self) -> None:
        """Initialize glossary (fetch or load from cache)"""
        if self._cache_loaded:
            return

        # Try loading from cache first
        if self.CACHE_FILE.exists():
            try:
                self._load_from_cache()
                logger.info(f"Loaded glossary from cache ({len(self._glossary or {})} terms)")
                self._cache_loaded = True
                return
            except Exception as e:
                logger.warning(f"Failed to load glossary cache: {e}")

        # Fetch from web
        try:
            await self._fetch_glossary()
            self._save_to_cache()
            logger.info(f"Fetched glossary from web ({len(self._glossary or {})} terms)")
            self._cache_loaded = True
        except Exception as e:
            logger.error(f"Failed to fetch glossary: {e}")
            # Initialize with empty glossary rather than failing
            self._glossary = self._get_fallback_glossary()
            self._cache_loaded = True

    def _load_from_cache(self) -> None:
        """Load glossary from local cache"""
        with self.CACHE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)

        self._glossary = {
            term_key: GlossaryTerm(
                term=term_data["term"],
                definition=term_data["definition"],
                category=term_data.get("category"),
                related_terms=term_data.get("related_terms", []),
            )
            for term_key, term_data in data.items()
        }

    def _save_to_cache(self) -> None:
        """Save glossary to local cache"""
        self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

        data = {
            term_key: {
                "term": term.term,
                "definition": term.definition,
                "category": term.category,
                "related_terms": term.related_terms,
            }
            for term_key, term in (self._glossary or {}).items()
        }

        with self.CACHE_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    async def _fetch_glossary(self) -> None:
        """
        Fetch glossary from legislative.gov.in

        Note: The actual site uses JavaScript/dynamic content, so this is a
        best-effort scraper. Uses fallback glossary if scraping fails.
        """
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                response = await client.get(self.GLOSSARY_URL)
                response.raise_for_status()
                html = response.text

                # Parse HTML for glossary terms
                terms = self._parse_glossary_html(html)

                if terms:
                    self._glossary = {
                        term.term.lower(): term
                        for term in terms
                    }
                else:
                    logger.warning("No terms parsed from HTML, using fallback glossary")
                    self._glossary = self._get_fallback_glossary()

            except Exception as e:
                logger.error(f"Failed to fetch glossary HTML: {e}")
                # Fallback to minimal hardcoded glossary
                self._glossary = self._get_fallback_glossary()

    def _parse_glossary_html(self, html: str) -> list[GlossaryTerm]:
        """
        Parse HTML to extract glossary terms.

        NOTE: This is a placeholder implementation. The actual legislative.gov.in
        glossary page structure needs to be analyzed and this parser updated accordingly.
        """
        terms = []

        # Try to find term/definition pairs using common HTML patterns
        # Pattern 1: <dt>term</dt><dd>definition</dd>
        pattern = r'<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

        for term_html, definition_html in matches:
            # Strip HTML tags
            term = re.sub(r'<[^>]+>', '', term_html).strip()
            definition = re.sub(r'<[^>]+>', '', definition_html).strip()

            if term and definition and len(definition) > 10:  # Basic validation
                terms.append(GlossaryTerm(
                    term=term,
                    definition=definition,
                ))

        return terms

    def _get_fallback_glossary(self) -> dict[str, GlossaryTerm]:
        """
        Fallback glossary with essential Indian legal terms.
        This is used when the website is unreachable or parsing fails.
        """
        terms = [
            GlossaryTerm(
                term="Writ Petition",
                definition="A formal written order issued by a court with administrative or judicial jurisdiction. In India, writ petitions under Articles 32 and 226 of the Constitution are filed in the Supreme Court and High Courts respectively.",
                category="Constitutional Law",
            ),
            GlossaryTerm(
                term="Mandamus",
                definition="A writ issued by a superior court to compel a lower court or a government officer to perform mandatory or purely ministerial duties correctly.",
                category="Constitutional Law",
            ),
            GlossaryTerm(
                term="Habeas Corpus",
                definition="A writ requiring a person under arrest to be brought before a judge or into court, ensuring that a prisoner can be released from unlawful detention.",
                category="Constitutional Law",
            ),
            GlossaryTerm(
                term="Certiorari",
                definition="A writ issued by a superior court for re-examination of an action of a lower court, tribunal, or quasi-judicial authority.",
                category="Constitutional Law",
            ),
            GlossaryTerm(
                term="Prohibition",
                definition="A writ issued by a higher court to prevent a lower court from exceeding its jurisdiction or acting contrary to the rules of natural justice.",
                category="Constitutional Law",
            ),
            GlossaryTerm(
                term="Quo Warranto",
                definition="A writ issued to inquire into the legality of claim of a person to a public office, preventing illegal usurpation of public office.",
                category="Constitutional Law",
            ),
            GlossaryTerm(
                term="Bail",
                definition="The temporary release of an accused person awaiting trial, sometimes on condition that a sum of money is lodged to guarantee their appearance in court.",
                category="Criminal Law",
            ),
            GlossaryTerm(
                term="Anticipatory Bail",
                definition="A direction to release a person on bail, issued even before the person is arrested. It is granted under Section 438 of the Code of Criminal Procedure.",
                category="Criminal Law",
            ),
            GlossaryTerm(
                term="Prima Facie",
                definition="At first sight; on the face of it. Evidence that is sufficient to establish a fact or raise a presumption of fact unless refuted.",
                category="Evidence",
            ),
            GlossaryTerm(
                term="Res Judicata",
                definition="A matter that has been adjudicated by a competent court and may not be pursued further by the same parties.",
                category="Civil Law",
            ),
            GlossaryTerm(
                term="Interim Relief",
                definition="Temporary or provisional relief granted by a court during the pendency of a case to preserve the rights of parties.",
                category="Civil Law",
            ),
            GlossaryTerm(
                term="Petitioner",
                definition="A person who presents a petition to a court. In writ proceedings, the person who files the writ petition.",
                category="Procedure",
            ),
            GlossaryTerm(
                term="Respondent",
                definition="The party against whom a petition is filed. In criminal appeals, typically the State or prosecution.",
                category="Procedure",
            ),
            GlossaryTerm(
                term="Article",
                definition="A numbered section in the Constitution of India. For example, Article 226 deals with the power of High Courts to issue writs.",
                category="Constitutional Law",
            ),
            GlossaryTerm(
                term="Section",
                definition="A numbered division of an Act or statute. For example, Section 498A IPC deals with cruelty by husband or relatives.",
                category="Statutory Law",
            ),
            GlossaryTerm(
                term="Cognizable Offense",
                definition="An offense for which a police officer may arrest without warrant, as per the First Schedule of the Code of Criminal Procedure.",
                category="Criminal Law",
            ),
            GlossaryTerm(
                term="Non-Cognizable Offense",
                definition="An offense for which a police officer has no authority to arrest without warrant.",
                category="Criminal Law",
            ),
            GlossaryTerm(
                term="FIR",
                definition="First Information Report. A written document prepared by the police when they receive information about the commission of a cognizable offense.",
                category="Criminal Law",
            ),
            GlossaryTerm(
                term="Charge Sheet",
                definition="A formal document prepared by police containing details of the offense and evidence collected during investigation, filed before a magistrate.",
                category="Criminal Law",
            ),
            GlossaryTerm(
                term="Quash",
                definition="To nullify, annul, or set aside. High Courts can quash FIRs or criminal proceedings under Section 482 CrPC.",
                category="Criminal Law",
            ),
        ]

        return {term.term.lower(): term for term in terms}

    async def lookup_term(self, term: str) -> Optional[GlossaryTerm]:
        """
        Look up a legal term in the glossary.

        Args:
            term: The term to look up (case-insensitive)

        Returns:
            GlossaryTerm if found, None otherwise
        """
        await self.initialize()

        if not self._glossary:
            return None

        # Try exact match first
        result = self._glossary.get(term.lower())
        if result:
            return result

        # Try partial match (find terms containing the search term)
        for key, glossary_term in self._glossary.items():
            if term.lower() in key or key in term.lower():
                return glossary_term

        return None

    async def verify_term_meaning(self, term: str, context: str) -> tuple[bool, Optional[str]]:
        """
        Verify if a term's usage matches its official definition using AI.

        Args:
            term: The legal term to verify
            context: The sentence/paragraph where the term is used

        Returns:
            Tuple of (is_correct, explanation)
        """
        glossary_term = await self.lookup_term(term)

        if not glossary_term:
            # Term not in glossary - assume it's okay but note it
            return (True, f"Term '{term}' not found in official glossary.")

        # Use LLM to verify usage matches definition
        if not settings.groq_api_key:
            return (True, "Cannot verify without LLM configured.")

        from langchain_groq import ChatGroq
        from langchain_core.messages import SystemMessage, HumanMessage
        from pydantic import SecretStr

        llm = ChatGroq(
            model=settings.default_llm_model,
            api_key=SecretStr(settings.groq_api_key),
            temperature=0.1,
        )

        messages = [
            SystemMessage(
                content=(
                    "You are a legal expert verifying the correct usage of legal terminology.\n"
                    "You will be given:\n"
                    "1. A legal term\n"
                    "2. Its official definition from the Legislative Department\n"
                    "3. The context in which it's being used\n\n"
                    "Your task: Determine if the term is being used correctly according to its official definition.\n"
                    "Respond with ONLY:\n"
                    "- 'CORRECT: [brief explanation]' if usage matches definition\n"
                    "- 'INCORRECT: [brief explanation]' if usage doesn't match definition"
                )
            ),
            HumanMessage(
                content=(
                    f"Term: {glossary_term.term}\n\n"
                    f"Official Definition: {glossary_term.definition}\n\n"
                    f"Context of Usage: {context}\n\n"
                    f"Is the term '{glossary_term.term}' being used correctly in this context?"
                )
            ),
        ]

        try:
            response = await llm.ainvoke(messages)
            result_text = str(response.content).strip()

            is_correct = result_text.upper().startswith("CORRECT")
            explanation = result_text.split(":", 1)[1].strip() if ":" in result_text else result_text

            return (is_correct, explanation)

        except Exception as e:
            logger.error(f"Failed to verify term usage: {e}")
            return (True, f"Verification failed: {e}")

# Global instance
_glossary_service: Optional[LegalGlossaryService] = None

def get_glossary_service() -> LegalGlossaryService:
    """Get or create the global glossary service instance"""
    global _glossary_service
    if _glossary_service is None:
        _glossary_service = LegalGlossaryService()
    return _glossary_service
