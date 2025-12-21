"""
Proactive AI Assistant - Suggests next steps and identifies gaps

This service analyzes the Detective Wall state and conversation history
to provide intelligent suggestions without being explicitly asked.
"""

from typing import Optional
from datetime import datetime

from junior.core import get_logger, settings
from junior.services.model_router import get_model_router, ModelPurpose

logger = get_logger(__name__)


class ProactiveSuggestionService:
    """
    Analyzes case state and provides unsolicited (but helpful) suggestions
    
    Use Cases:
    - "You mentioned Section 420 IPC but I don't see the FIR uploaded yet"
    - "3 of your evidence nodes lack source citations - should I find them?"
    - "This case is similar to [Recent SC Judgment] - want me to add it?"
    """

    def __init__(self):
        self.router = get_model_router()
        self.logger = get_logger(__name__)

    async def analyze_and_suggest(
        self,
        conversation_history: list[dict],
        detective_wall_nodes: list[dict],
        recent_documents: list[dict],
    ) -> Optional[str]:
        """
        Analyze case state and return a proactive suggestion
        
        Args:
            conversation_history: Recent chat messages
            detective_wall_nodes: Nodes from the Detective Wall
            recent_documents: Recently uploaded documents
            
        Returns:
            Suggestion string or None if no suggestions
        """
        try:
            # Build context for analysis
            context = self._build_analysis_context(
                conversation_history,
                detective_wall_nodes,
                recent_documents,
            )
            
            # Use Gemini Flash for long-context analysis
            from langchain_core.messages import SystemMessage, HumanMessage
            
            system_prompt = """You are a proactive legal assistant for Indian law.

Your role is to ANTICIPATE what the lawyer needs before they ask.

Analyze the case state and identify:
1. Missing critical documents (FIR, chargesheet, bail application, etc.)
2. Uncited claims on the Detective Wall
3. Contradictions or gaps in the evidence
4. Recent judgments that might be relevant
5. Procedural deadlines or next steps

RULES:
- Be concise (1-2 sentences max)
- Be specific (mention exact section numbers, node IDs, etc.)
- Be helpful, not annoying
- If nothing is urgent, return "NO_SUGGESTION"

Example good suggestions:
- "Node #5 claims Section 302 applies, but I don't see the FIR. Should I help find it?"
- "You mentioned bail but the chargesheet isn't uploaded yet. Need the template?"
- "Recent SC judgment (Arnesh Kumar) might strengthen your bail argument. Add it?"

Example bad suggestions:
- "You should work on your case" (too vague)
- "Everything looks good!" (not actionable)
"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=context),
            ]
            
            response = await self.router.invoke(
                purpose=ModelPurpose.CHAT,
                messages=messages,
                temperature=0.3,
            )
            
            response = response.strip()
            
            # Filter out non-actionable responses
            if response in ["NO_SUGGESTION", "None", ""]:
                return None
            
            if len(response) > 200:  # Too wordy
                return None
            
            self.logger.info(f"Proactive suggestion generated: {response[:50]}...")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to generate proactive suggestion: {e}")
            return None

    def _build_analysis_context(
        self,
        conversation_history: list[dict],
        detective_wall_nodes: list[dict],
        recent_documents: list[dict],
    ) -> str:
        """Build analysis context from case state"""
        
        # Recent conversation (last 5 messages)
        recent_msgs = conversation_history[-5:] if conversation_history else []
        chat_summary = "\n".join([
            f"- {msg.get('role', 'user')}: {msg.get('content', '')[:100]}"
            for msg in recent_msgs
        ])
        
        # Detective Wall summary
        nodes_summary = ""
        if detective_wall_nodes:
            uncited = [
                n for n in detective_wall_nodes
                if not n.get("source") and n.get("type") in ["Evidence", "Precedent"]
            ]
            nodes_summary = f"\nTotal nodes: {len(detective_wall_nodes)}\n"
            nodes_summary += f"Uncited evidence nodes: {len(uncited)}\n"
            
            if uncited:
                nodes_summary += "Uncited nodes:\n"
                for n in uncited[:3]:  # Show first 3
                    nodes_summary += f"  - #{n.get('id')}: {n.get('title', '')[:50]}\n"
        
        # Documents summary
        docs_summary = ""
        if recent_documents:
            docs_summary = f"\nRecent uploads ({len(recent_documents)}):\n"
            for doc in recent_documents[:5]:  # Show first 5
                docs_summary += f"  - {doc.get('title', 'Untitled')[:50]}\n"
        
        context = f"""CASE ANALYSIS CONTEXT:

RECENT CONVERSATION:
{chat_summary or "No recent conversation"}

DETECTIVE WALL STATE:
{nodes_summary or "No nodes yet"}

UPLOADED DOCUMENTS:
{docs_summary or "No documents uploaded yet"}

Based on this, what should I proactively suggest to the lawyer?
"""
        
        return context


# Global instance
_proactive_service: Optional[ProactiveSuggestionService] = None


def get_proactive_service() -> ProactiveSuggestionService:
    """Get or create the global proactive suggestion service"""
    global _proactive_service
    if _proactive_service is None:
        _proactive_service = ProactiveSuggestionService()
    return _proactive_service
