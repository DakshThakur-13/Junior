"""
Critic Agent - Validates research and identifies weaknesses
"""

from typing import Optional

from junior.core.types import AgentRole, CaseStatus
from .base import BaseAgent, AgentState

class CriticAgent(BaseAgent):
    """
    The Critic Agent is responsible for:
    1. Validating all citations for accuracy
    2. Identifying logical weaknesses in arguments
    3. Playing "Devil's Advocate" to stress-test the research
    4. Ensuring no hallucinated citations slip through
    5. Checking for overruled or distinguished cases
    """

    role = AgentRole.CRITIC

    @property
    def system_prompt(self) -> str:
        return """You are a Senior Advocate and former Additional Solicitor General with 35 years at the Indian Bar. You are known as the most exacting legal fact-checker in the country. Your critique is relied upon before Supreme Court Constitution Benches.

YOUR MANDATE: Ruthlessly validate every citation, spot every logical gap, and assign a rigorous confidence score.

INDIAN COURT HIERARCHY (for precedent assessment):
  SC Constitution Bench (5+ judges) > SC 3-Judge Bench > SC Division Bench > Single SC Judge
  > High Court Division Bench > HC Single Judge > District Court

KNOWN TRAPS TO CATCH:
  - Cases decided pre-1973 that may conflict with Basic Structure doctrine
  - High Court judgments from other states (persuasive, not binding)
  - Cases where a subsequent larger bench has diluted or overruled the ratio
  - Obiter dicta being cited as binding ratio
  - Section numbers changed after codification (IPC → BNS 2023, CrPC → BNSS 2023)
  - Judgments under challenge / pending larger bench reference

VALIDATION CHECKLIST (assess each citation):
  ☐ Does the document actually contain this citation?
  ☐ Is the paragraph number accurate to the content cited?
  ☐ Is the legal principle stated correctly (not paraphrased beyond recognition)?
  ☐ Has this case been overruled, distinguished, or affirmed by a later bench?
  ☐ Is this ratio decidendi or obiter dicta?
  ☐ Is the court from the correct jurisdiction?
  ☐ Does a larger SC bench exist on the same point?
  ☐ Has the underlying statute been amended since this judgment?

MULTI-DIMENSIONAL SCORING (score each out of 10, report all four):
  A. Citation Accuracy  – Are citations real, verifiable, paragraph-accurate?
  B. Legal Logic        – Do arguments flow correctly? Are principles applied rightly?
  C. Hierarchy Respect  – Is SC authority prioritised? HC jurisdiction noted?
  D. Coverage           – Are there missing angles the opposing counsel will exploit?

  OVERALL SCORE = (A×0.35 + B×0.30 + C×0.20 + D×0.15)

OUTPUT FORMAT:
For each citation:
  Citation: [case name and para]
  Verification: ✅ VERIFIED / ⚠️ CAUTION / ❌ INVALID
  Issue: [exact problem if any]
  Recommendation: [concrete fix]

Overall Assessment:
  Score A (Citation Accuracy): X/10
  Score B (Legal Logic): X/10
  Score C (Hierarchy Respect): X/10
  Score D (Coverage): X/10
  Strength Score: X/10  [computed weighted average]
  Major Weaknesses:
    - [bullet list]
  Suggested Improvements:
    - [bullet list]
  Missing Authorities: [cases that SHOULD have been cited but weren’t]
  Ready for Court: YES / NEEDS REVISION / NO

Be surgical. A lawyer’s career depends on your thoroughness."""

    async def process(self, state: AgentState) -> AgentState:
        """
        Validate research and identify weaknesses

        Args:
            state: Current workflow state with research notes and citations

        Returns:
            Updated state with critiques and revision flags
        """
        self.logger.info(f"Critiquing research with {len(state.citations)} citations...")

        # Build the critique prompt
        prompt = self._build_critique_prompt(state)

        # Get LLM response
        response = await self.invoke_llm(prompt)

        # Parse and process the critique
        critique_results = self._parse_critique_response(response)

        # Update state
        state.critiques.append(response)
        state.needs_revision = critique_results["needs_revision"]
        state.confidence_score = critique_results["confidence_score"]

        # Populate critic_issues for the Researcher's targeted re-search loop
        if critique_results["issues"]:
            state.critic_issues = critique_results["issues"]
            self.logger.info(
                f"Identified {len(state.critic_issues)} specific issues for re-search: "
                + "; ".join(state.critic_issues[:2])
            )

        # Filter out invalid citations
        if critique_results["invalid_citations"]:
            self._flag_invalid_citations(state, critique_results["invalid_citations"])

        self.logger.info(
            f"Critique complete. Confidence: {state.confidence_score:.1f}/10, "
            f"Needs revision: {state.needs_revision}"
        )

        return state

    def _build_critique_prompt(self, state: AgentState) -> str:
        """Build the prompt for critique"""
        citations_text = self.format_citations_for_prompt(state.citations)
        documents_text = self.format_documents_for_prompt(state.documents)

        prompt = f"""ORIGINAL QUERY:
{state.query}

RESEARCH NOTES TO VALIDATE:
{chr(10).join(state.research_notes)}

CITATIONS TO VERIFY:
{citations_text}

SOURCE DOCUMENTS (for verification):
{documents_text}

DRAFT RESPONSE (if any):
{state.draft or 'No draft yet - this is early-stage critique.'}

TASK:
1. Verify EACH citation against the source documents
2. Identify any logical weaknesses or gaps in the research
3. Play Devil's Advocate - what would opposing counsel argue?
4. Check for overruled or distinguished cases
5. Assess overall readiness for court submission

Be thorough and uncompromising. A lawyer's reputation depends on accuracy."""

        return prompt

    def _parse_critique_response(self, response: str) -> dict:
        """
        Parse the critique response using multi-dimensional scoring.

        Dimensions (matching the new system prompt):
          A. Citation Accuracy  (weight 0.35)
          B. Legal Logic        (weight 0.30)
          C. Hierarchy Respect  (weight 0.20)
          D. Coverage           (weight 0.15)

        Returns:
            dict with needs_revision, confidence_score, invalid_citations, issues
        """
        import re

        response_lower = response.lower()

        # --- Determine if revision is needed ---
        needs_revision = any(kw in response_lower for kw in (
            "needs revision", "❌ invalid", "not ready", "major weakness",
            "missing authorities", "no citation", "unsupported claim",
        ))

        # --- Multi-dimensional score extraction ---
        def _extract_dim_score(label: str) -> Optional[float]:
            """Extract 'Score X (Label): Y/10' or 'Label: Y/10' patterns."""
            patterns = [
                rf"score\s+\w+\s+\({re.escape(label)}\)[:\s]+(\d+(?:\.\d+)?)",
                rf"{re.escape(label)}[:\s]+(\d+(?:\.\d+)?)\s*/\s*10",
                rf"{re.escape(label.lower())}[:\s]+(\d+(?:\.\d+)?)",
            ]
            for pat in patterns:
                m = re.search(pat, response_lower)
                if m:
                    val = float(m.group(1))
                    return min(10.0, max(0.0, val))
            return None

        score_a = _extract_dim_score("Citation Accuracy")
        score_b = _extract_dim_score("Legal Logic")
        score_c = _extract_dim_score("Hierarchy Respect")
        score_d = _extract_dim_score("Coverage")

        # Try to read the overall "Strength Score" the LLM emitted directly
        overall_match = re.search(
            r"strength\s+score[:\s]+(\d+(?:\.\d+)?)\s*/?\s*10?",
            response_lower,
        )

        if overall_match:
            confidence_score = min(10.0, max(0.0, float(overall_match.group(1))))
        elif any(s is not None for s in (score_a, score_b, score_c, score_d)):
            # Compute weighted average from available dimensions
            weights = {
                "a": (score_a, 0.35),
                "b": (score_b, 0.30),
                "c": (score_c, 0.20),
                "d": (score_d, 0.15),
            }
            total_w = 0.0
            total_score = 0.0
            for _dim, (sc, wt) in weights.items():
                if sc is not None:
                    total_score += sc * wt
                    total_w += wt
            confidence_score = round(total_score / total_w, 1) if total_w > 0 else 5.0
        else:
            # Keyword fallback
            if "✅" in response and "❌" not in response and "⚠️" not in response:
                confidence_score = 8.5
            elif "strong" in response_lower and "verified" in response_lower:
                confidence_score = 8.0
            elif "❌" in response:
                confidence_score = 3.0
            elif "⚠️" in response or "caution" in response_lower:
                confidence_score = 5.5
            else:
                confidence_score = 6.0

        # --- Extract invalid citations ---
        invalid_citations: list[str] = []
        issues: list[str] = []
        lines = response.split("\n")

        for line in lines:
            stripped = line.strip()
            if "❌" in line or "invalid" in line.lower():
                if "citation:" in line.lower():
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        invalid_citations.append(parts[1].strip())

            # Harvest bullet points under weakness/improvement/missing sections
            if stripped.startswith(("- ", "• ", "* ")):
                issue_text = stripped.lstrip("-•* ").strip()
                if len(issue_text) > 10:
                    # Check if within a relevant section heading in the response
                    pos = response.find(stripped)
                    ctx = response[max(0, pos - 300): pos].lower()
                    if any(kw in ctx for kw in (
                        "major weakness", "suggested improvement", "missing", "gap", "issue:", "weakness:"
                    )):
                        issues.append(issue_text)

        # Keyword fallback for issues
        if not issues and needs_revision:
            for line in lines:
                s = line.strip()
                if len(s) > 30 and any(kw in s.lower() for kw in (
                    "missing", "weak", "no citation", "unsupported", "gap", "lacking", "missing authorities"
                )):
                    issues.append(s)
                    if len(issues) >= 5:
                        break

        self.logger.debug(
            f"[Critic] Scores — A:{score_a} B:{score_b} C:{score_c} D:{score_d} "
            f"→ overall={confidence_score:.1f}, revision={needs_revision}"
        )

        return {
            "needs_revision": needs_revision,
            "confidence_score": confidence_score,
            "score_citation_accuracy": score_a,
            "score_legal_logic": score_b,
            "score_hierarchy_respect": score_c,
            "score_coverage": score_d,
            "invalid_citations": invalid_citations,
            "issues": issues,
            "full_critique": response,
        }

        return {
            "needs_revision": needs_revision,
            "confidence_score": confidence_score,
            "invalid_citations": invalid_citations,
            "issues": issues,
            "full_critique": response,
        }

    def _flag_invalid_citations(self, state: AgentState, invalid_refs: list[str]) -> None:
        """
        Flag citations as invalid based on critique

        Args:
            state: Current workflow state
            invalid_refs: List of invalid citation references
        """
        for citation in state.citations:
            for invalid_ref in invalid_refs:
                if (
                    citation.case_name.lower() in invalid_ref.lower() or
                    invalid_ref.lower() in citation.case_name.lower()
                ):
                    # Mark as overruled/invalid
                    citation.status = CaseStatus.OVERRULED
                    self.logger.warning(f"Flagged invalid citation: {citation.case_name}")

class DevilsAdvocateAgent(CriticAgent):
    """
    Specialized Critic that simulates opposing counsel
    Used in the "War Room" feature for stress-testing arguments
    """

    @property
    def system_prompt(self) -> str:
        return """You are a seasoned opposing counsel in an Indian court. Your job is to DESTROY the legal arguments presented to you. You must:

1. ATTACK every weak point in the opponent's case
2. FIND contradictions and inconsistencies
3. CITE counter-precedents that undermine their position
4. QUESTION the applicability of their cited cases
5. EXPLOIT any procedural or jurisdictional weaknesses

Your goal is to prepare your client (the user) for the WORST possible arguments they might face in court. Be aggressive but professional.

ATTACK VECTORS:
- Distinguishing cited cases on facts
- Finding higher court decisions that contradict
- Procedural defects (limitation, locus standi, etc.)
- Jurisdictional challenges
- Evidentiary gaps
- Policy arguments

OUTPUT FORMAT:
## OPPOSING COUNSEL'S ARGUMENTS

### Attack Point 1: [Title]
**The Weakness:** [What's wrong with their argument]
**Counter-Citation:** [Case that contradicts their position]
**Suggested Attack:** [How I would argue this in court]

[Repeat for each attack point]

### OVERALL VULNERABILITY ASSESSMENT
- Critical Weaknesses: [List]
- Moderate Risks: [List]
- Preparation Recommendations: [How to defend against these attacks]

Remember: Better to find weaknesses now than be surprised in court."""

    async def simulate_opposition(self, state: AgentState) -> dict:
        """
        Simulate opposing counsel's attack on the case

        Args:
            state: Current workflow state with research and draft

        Returns:
            Dictionary with opposition arguments and recommendations
        """
        self.logger.info("Simulating opposing counsel attack...")

        protocol_id = None
        try:
            protocol_id = (state.metadata or {}).get("protocol_id")
        except Exception:
            protocol_id = None

        protocol_context = ""
        if protocol_id:
            try:
                from junior.services.lawyer_protocols import protocol_brief

                protocol_context = protocol_brief(protocol_id).strip()
            except Exception:
                protocol_context = ""

        prompt = f"""THE OPPOSING PARTY'S LEGAL ARGUMENTS:
{state.query}

    {('LAWYER PROTOCOL (for structured attack):\n' + protocol_context + '\n') if protocol_context else ''}

THEIR RESEARCH AND CITATIONS:
{chr(10).join(state.research_notes)}

THEIR CITATIONS:
{self.format_citations_for_prompt(state.citations)}

THEIR DRAFT ARGUMENT:
{state.draft or 'No formal draft yet.'}

YOUR TASK AS OPPOSING COUNSEL:
Tear apart these arguments. Find every weakness. Prepare counter-arguments.
Be merciless but legally sound."""

        response = await self.invoke_llm(prompt)

        return {
            "opposition_arguments": response,
            "attack_count": response.lower().count("attack point"),
        }
