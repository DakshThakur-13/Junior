"""
Writer Agent - Synthesizes research into legal prose
"""

from typing import Optional

from junior.core.types import AgentRole
from .base import BaseAgent, AgentState

class WriterAgent(BaseAgent):
    """
    The Writer Agent is responsible for:
    1. Synthesizing research into coherent legal prose
    2. Ensuring proper citation format throughout
    3. Maintaining appropriate legal register and tone
    4. Structuring arguments logically
    5. Producing court-ready documents
    """

    role = AgentRole.WRITER

    @property
    def system_prompt(self) -> str:
        return """You are a celebrated legal drafter who has authored winning petitions before the Supreme Court of India, Delhi High Court, and Bombay High Court. Your work is cited as a model of clarity and precision. You now draft on behalf of Junior AI's clients.

INDIAN DRAFTING STANDARDS:
  - Language: Formal English; avoid contractions and colloquialisms
  - Tone: Respectful, measured, persuasive — never inflammatory
  - Every substantive legal proposition MUST carry a pinpoint citation
  - Distinguish clearly between binding Supreme Court authority and persuasive HC authority
  - Identify the applicable statute AND the relevant amendment in force on the date of the facts

MANDATORY PHRASEBOOK FOR INDIAN COURTS:
  Submissions:   "It is most humbly submitted that..."
  Contentions:   "It is respectfully contended that..."
  Reliance:      "Strong reliance is placed upon..."
  Distinction:   "The aforesaid authority is distinguishable on facts inasmuch as..."
  Concession:    "Without prejudice to the aforesaid, it is submitted in the alternative that..."
  Prayer:        "In the premises aforesaid, it is most respectfully prayed that..."

CITATION FORMAT (mandatory):
  Supreme Court:  [Case Name] (Year) Volume SCC Page, at Para X
  High Court:     [Case Name] (Year) Volume [Reporter] Page, at Para X
  Statute:        Section X of the [Act Name], [Year]
  Constitutional: Article X of the Constitution of India
  Inline:         (See: [Case Name], supra, at Para X)

IRAC STRUCTURE (use for each legal issue):
  ISSUE     — State the precise legal question arising on facts
  RULE      — State the applicable legal principle with primary authority
  APPLICATION — Apply the rule to the specific facts of the client's case
  CONCLUSION — State the logical outcome and connect to relief sought

DOCUMENT STRUCTURE:
  I.    Synopsis / Executive Summary
  II.   Facts in Brief (chronological)
  III.  Questions of Law
  IV.   Arguments (with Roman-numeral sub-headings per issue)
        A. [Issue 1 — strongest argument first]
        B. [Issue 2]
        ...
  V.    Counter-Arguments Anticipated & Rebuttals
  VI.   Prayer / Relief Sought

QUALITY GATES before finalising:
  ✓ Every paragraph of argument has at least one citation
  ✓ No citation appears without a paragraph number
  ✓ Binding SC authority cited in preference to HC where both available
  ✓ Statutory provisions referenced with current section numbers (BNS/BNSS if post-2023)
  ✓ Opposing arguments anticipated and rebutted

Produce work that a Chief Justice would find impeccable."""

    async def process(self, state: AgentState) -> AgentState:
        """
        Synthesize research into a legal draft

        Args:
            state: Current workflow state with validated research

        Returns:
            Updated state with draft document
        """
        self.logger.info("Drafting legal document...")

        # Build the writing prompt
        prompt = self._build_writing_prompt(state)

        # Get LLM response
        response = await self.invoke_llm(prompt)

        # Update state
        state.draft = response

        # If we've been through critique and confidence is high, finalize
        if state.confidence_score >= 7.0 and not state.needs_revision:
            state.final_output = self._format_final_output(response, state)

        self.logger.info(f"Draft complete. Length: {len(response)} characters")

        return state

    def _build_writing_prompt(self, state: AgentState) -> str:
        """Build the prompt for legal writing"""
        citations_text = self.format_citations_for_prompt(
            [c for c in state.citations if c.status.value != "overruled"]
        )

        # Include critique feedback if available
        critique_feedback = ""
        if state.critiques:
            critique_feedback = f"""
CRITIQUE FEEDBACK TO ADDRESS:
{state.critiques[-1]}
"""

        prompt = f"""LEGAL QUERY/ISSUE:
{state.query}

VERIFIED RESEARCH NOTES:
{chr(10).join(state.research_notes)}

VALID CITATIONS TO USE:
{citations_text}

{critique_feedback}

PREVIOUS DRAFT (if revision):
{state.draft or 'No previous draft - this is the first write.'}

TASK:
Write a comprehensive legal response that:
1. Directly addresses the legal query
2. Cites ALL relevant cases with pinpoint paragraph references
3. Structures arguments logically
4. Uses appropriate legal language for Indian courts
5. Includes a clear conclusion

IMPORTANT:
- Every legal proposition MUST be supported by a citation
- Format citations properly: [Case Name] (Year) at Para [X]
- Flag any areas where the law is unsettled
- Note any caveats or limitations"""

        return prompt

    def _format_final_output(self, draft: str, state: AgentState) -> str:
        """
        Format the final output with proper structure and metadata

        Args:
            draft: The draft text
            state: Current workflow state

        Returns:
            Formatted final output
        """
        # Add header
        header = """════════════════════════════════════════════════════════════
                        LEGAL RESEARCH MEMORANDUM
                    Generated by Junior AI Legal Assistant
════════════════════════════════════════════════════════════

⚠️ AI DRAFT - INTERNAL USE ONLY - VERIFY ALL CITATIONS ⚠️

"""

        # Add citations appendix
        citations_appendix = "\n\n" + "═" * 60 + "\n"
        citations_appendix += "                    CITATIONS REFERENCED\n"
        citations_appendix += "═" * 60 + "\n\n"

        for i, citation in enumerate(state.citations, 1):
            if citation.status.value != "overruled":
                status_emoji = "🟢" if citation.status.value == "good_law" else "🟡"
                citations_appendix += f"{i}. {status_emoji} {citation.formatted}\n"

        # Add footer
        footer = f"""

═══════════════════════════════════════════════════════════
Research Confidence Score: {state.confidence_score:.1f}/10
Iterations: {state.iteration}
Citations Used: {len([c for c in state.citations if c.status.value != 'overruled'])}
═══════════════════════════════════════════════════════════

DISCLAIMER: This document was generated by an AI system. All
citations and legal propositions must be independently verified
before use in any legal proceeding. This document does not
constitute legal advice.
"""

        return header + draft + citations_appendix + footer

    async def format_for_court(
        self,
        state: AgentState,
        court_type: str = "high_court",
        document_type: str = "written_statement",
    ) -> str:
        """
        Format the draft according to specific court requirements

        Args:
            state: Current workflow state with final output
            court_type: Target court (supreme_court, high_court, district_court)
            document_type: Type of document (writ_petition, written_statement, etc.)

        Returns:
            Court-formatted document
        """
        format_prompt = f"""FORMAT THE FOLLOWING LEGAL CONTENT FOR:
Court: {court_type.replace('_', ' ').title()}
Document Type: {document_type.replace('_', ' ').title()}

CONTENT TO FORMAT:
{state.final_output or state.draft}

FORMATTING REQUIREMENTS:
1. Proper cause title format
2. Appropriate paragraph numbering
3. Correct margin and spacing conventions
4. Standard prayer format for {document_type}
5. Verification/affidavit section if required

OUTPUT: The fully formatted document ready for filing."""

        formatted = await self.invoke_llm(format_prompt)
        return formatted

class TranslationWriter(WriterAgent):
    """
    Specialized Writer for multilingual output
    Handles the "Hinglish Bridge" feature
    """

    async def translate_with_legal_terms(
        self,
        state: AgentState,
        target_language: str = "hi",
    ) -> str:
        """
        Translate the draft while preserving legal terminology in English

        Args:
            state: Current workflow state with draft
            target_language: Target language code (hi, mr, ta, etc.)

        Returns:
            Translated document with English legal terms preserved
        """
        language_names = {
            "hi": "Hindi",
            "mr": "Marathi",
            "ta": "Tamil",
            "te": "Telugu",
            "bn": "Bengali",
            "gu": "Gujarati",
            "kn": "Kannada",
            "ml": "Malayalam",
            "pa": "Punjabi",
        }

        target_lang_name = language_names.get(target_language, "Hindi")

        prompt = f"""TRANSLATE THE FOLLOWING LEGAL DOCUMENT TO {target_lang_name.upper()}:

{state.final_output or state.draft}

TRANSLATION RULES:
1. PRESERVE all legal terms in English:
   - Case names
   - Latin maxims (e.g., "res judicata", "stare decisis")
   - Technical terms (e.g., "Interim Relief", "Locus Standi", "Prima Facie")
   - Statutory references (e.g., "Section 34 of the Arbitration Act")
   - Citation formats

2. Translate the explanatory text to {target_lang_name}
3. Maintain the document structure
4. Use formal legal register in {target_lang_name}

OUTPUT: The translated document with legal terms preserved in English."""

        translated = await self.invoke_llm(prompt)
        return translated
