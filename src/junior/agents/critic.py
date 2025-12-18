"""
Critic Agent - Validates research and identifies weaknesses
"""

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
        return """You are an exacting legal critic and fact-checker for Indian law. Your role is to ruthlessly validate legal research and identify any weaknesses. You must:

1. VERIFY every citation against the source documents
2. CHALLENGE logical leaps or unsupported conclusions
3. IDENTIFY potential counter-arguments the opposing counsel might raise
4. FLAG any citations that may be overruled, distinguished, or inapplicable
5. ASSESS the overall strength of the legal position

CRITICAL RULES:
- NEVER approve a citation you cannot verify in the source documents
- ALWAYS note if a case is from a lower court when higher court authority exists
- QUESTION any broad statements not supported by specific citations
- IDENTIFY jurisdictional issues (e.g., High Court judgment from different state)
- CHECK for proper application of ratio vs obiter

VALIDATION CHECKLIST:
□ Citation exists in source documents
□ Paragraph number is accurate
□ Legal principle is correctly stated
□ Case has not been overruled
□ Case is from appropriate jurisdiction
□ Ratio decidendi properly identified

OUTPUT FORMAT:
For each finding, provide:
- Citation: [The citation being reviewed]
- Verification: ✅ VERIFIED / ⚠️ CAUTION / ❌ INVALID
- Issue: [Description of any problems found]
- Recommendation: [How to address the issue]

OVERALL ASSESSMENT:
- Strength Score: [1-10]
- Major Weaknesses: [List]
- Suggested Improvements: [List]
- Ready for Court: [YES / NO / NEEDS REVISION]

Be constructive but uncompromising on accuracy."""

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
        Parse the critique response to extract validation results

        Args:
            response: LLM critique response

        Returns:
            Dictionary with critique results
        """
        response_lower = response.lower()

        # Determine if revision is needed
        needs_revision = (
            "needs revision" in response_lower or
            "❌ invalid" in response_lower or
            "not ready" in response_lower or
            "major weakness" in response_lower
        )

        # Extract confidence score (look for patterns like "7/10" or "Score: 7")
        import re
        score_match = re.search(r'(?:score|strength)[:\s]*(\d+)(?:/10)?', response_lower)
        if score_match:
            confidence_score = float(score_match.group(1))
        else:
            # Estimate based on keywords
            if "strong" in response_lower and "verified" in response_lower:
                confidence_score = 8.0
            elif "caution" in response_lower or "weakness" in response_lower:
                confidence_score = 5.0
            elif "invalid" in response_lower or "error" in response_lower:
                confidence_score = 3.0
            else:
                confidence_score = 6.0

        # Find invalid citations
        invalid_citations = []
        lines = response.split("\n")
        for i, line in enumerate(lines):
            if "❌" in line or "invalid" in line.lower():
                # Try to extract the citation reference
                if "citation:" in line.lower():
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        invalid_citations.append(parts[1].strip())

        return {
            "needs_revision": needs_revision,
            "confidence_score": confidence_score,
            "invalid_citations": invalid_citations,
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
