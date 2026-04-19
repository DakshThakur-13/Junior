"""
Conversational Chat Service - Natural ChatGPT-like experience for legal queries

This service provides:
- Streaming responses (words appear in real-time)
- Natural conversation (not robotic)
- Smart context awareness (legal focus but friendly)
- Fast responses (no heavy workflows for simple questions)
"""

from typing import AsyncGenerator, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from junior.core import get_logger, settings
from junior.services.model_router import ModelRouter, ModelPurpose

logger = get_logger(__name__)


LEGAL_ASSISTANT_PROMPT = """You are Junior - a friendly, knowledgeable legal AI assistant.

Your personality:
- Warm and approachable, not cold or robotic
- Expert in law, but you explain things clearly
- Conversational and natural, like talking to a smart friend
- You use "I" and "you" naturally
- You ask clarifying questions when needed

Your expertise:
- Indian law, legal procedures, case law, statutes
- You cite sources when you can
- You're honest when you don't know something
- You suggest next steps and practical advice

Your style:
- Short paragraphs, easy to read
- Use bullet points for lists
- Bold key terms occasionally
- Natural, flowing conversation

Remember:
- You're helpful, but NOT providing formal legal advice (users should consult lawyers)
- You're focused on law, but you can chat naturally about the user's situation
- You're fast and efficient - get to the point while being friendly
"""

RESEARCH_MODE_PROMPT = """Research mode is ON.

Requirements:
- Be precise and legally grounded.
- When citing law/cases, include source URLs when available.
- Separate facts, assumptions, and legal inference.
- End with a short checklist of next actions for counsel.
- If uncertain, state uncertainty explicitly.
"""


class ConversationalChat:
    """Natural, ChatGPT-like chat for legal queries"""
    
    def __init__(self):
        self.model_router = ModelRouter()
        self.logger = get_logger(__name__)
    
    async def stream_response(
        self,
        message: str,
        conversation_history: list[dict],
        use_research: bool = False
    ) -> AsyncGenerator[str, None]:
        """
        Stream a natural conversational response
        
        Args:
            message: User's message
            conversation_history: Previous messages [{"role": "user|assistant", "content": "..."}]
            use_research: If True, do deep research. If False, just chat naturally
            
        Yields:
            Chunks of the response as they're generated
        """
        try:
            # Build conversation context
            messages = [SystemMessage(content=LEGAL_ASSISTANT_PROMPT)]
            if use_research:
                messages.append(SystemMessage(content=RESEARCH_MODE_PROMPT))
            
            # Add conversation history (last 6 messages for context)
            for msg in conversation_history[-6:]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                else:
                    messages.append(AIMessage(content=msg["content"]))
            
            # Add current message
            messages.append(HumanMessage(content=message))
            
            # Get the right model (Perplexity for chat - has online search built-in)
            llm = self.model_router.get_model(
                purpose=ModelPurpose.CHAT,
                temperature=0.35 if use_research else 0.7,
                max_tokens=3072 if use_research else 2048,
            )
            
            # Stream the response
            async for chunk in llm.astream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
                    
        except Exception as e:
            self.logger.error(f"Error in conversational chat: {e}", exc_info=True)
            yield f"\n\nI apologize, I'm having trouble responding right now. Could you try rephrasing your question? ({str(e)[:100]})"
    
    def should_use_deep_research(self, message: str) -> bool:
        """
        Determine if we should use the full research workflow or just chat
        
        Simple heuristic:
        - Long messages with specific case details → Deep research
        - Questions about specific laws/cases → Deep research  
        - General questions, clarifications → Fast chat
        """
        # Keywords that suggest deep research needed
        research_keywords = [
            "case", "cases", "precedent", "section", "act", "statute",
            "judgment", "court", "supreme court", "high court",
            "legal opinion", "analysis", "research"
        ]
        
        message_lower = message.lower()
        
        # If message is very short, just chat
        if len(message.split()) < 10:
            return False
        
        # If contains research keywords
        if any(keyword in message_lower for keyword in research_keywords):
            return True
        
        return False


# Global instance
conversational_chat = ConversationalChat()
