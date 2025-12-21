"""
Base Agent class for all Junior AI agents
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from langchain_groq import ChatGroq
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field, SecretStr

from junior.core import settings, get_logger
from junior.core.types import AgentRole, AgentMessage, Citation
from junior.core.exceptions import LLMNotConfiguredError

logger = get_logger(__name__)

def _make_hf_endpoint(HuggingFaceEndpoint, **kwargs):
    """Create HuggingFaceEndpoint across langchain_huggingface versions.

    Some versions use `repo_id=...`, others use `model=...`.
    """
    try:
        return HuggingFaceEndpoint(**kwargs)
    except TypeError:
        if "repo_id" in kwargs and "model" not in kwargs:
            alt_kwargs = dict(kwargs)
            alt_kwargs["model"] = alt_kwargs.pop("repo_id")
            return HuggingFaceEndpoint(**alt_kwargs)
        raise

class AgentState(BaseModel):
    """State passed between agents in the workflow"""
    query: str
    language: str = "en"
    documents: list[dict] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    research_notes: list[str] = Field(default_factory=list)
    critiques: list[str] = Field(default_factory=list)
    draft: Optional[str] = None
    final_output: Optional[str] = None
    iteration: int = 0
    max_iterations: int = 3
    confidence_score: float = 0.0
    needs_revision: bool = False
    metadata: dict = Field(default_factory=dict)

class BaseAgent(ABC):
    """
    Base class for all AI agents in Junior

    Each agent has a specific role in the Agentic RAG workflow:
    - Researcher: Finds relevant case law and extracts information
    - Critic: Validates citations and identifies weaknesses
    - Writer: Synthesizes research into legal prose
    """

    role: AgentRole
    use_model_router: bool = True  # Enable multi-model architecture

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.1,
        use_model_router: bool = True,
    ):
        self.model_name = model_name or settings.default_llm_model
        self.temperature = temperature
        self.use_model_router = use_model_router
        self._llm: Optional[BaseChatModel] = None
        self.logger = get_logger(f"agent.{self.role.value}")

    @property
    def llm(self) -> BaseChatModel:
        """Get or create LLM instance using model router or legacy method"""
        if self._llm is None:
            # NEW: Use Model Router for specialized models
            if self.use_model_router:
                try:
                    from junior.services.model_router import get_model_router, ModelPurpose
                    
                    # Map agent role to model purpose
                    purpose_map = {
                        AgentRole.RESEARCHER: ModelPurpose.RESEARCHER,
                        AgentRole.CRITIC: ModelPurpose.CRITIC,
                        AgentRole.WRITER: ModelPurpose.WRITER,
                    }
                    
                    purpose = purpose_map.get(self.role, ModelPurpose.GENERAL)
                    router = get_model_router()
                    self._llm = router.get_model(purpose=purpose, temperature=self.temperature)
                    self.logger.info(f"Using specialized model via router: {purpose.value}")
                    return self._llm
                except Exception as e:
                    self.logger.warning(f"Model router failed: {e}. Falling back to legacy LLM.")
                    # Fall through to legacy method
            
            # LEGACY: Original LLM initialization (kept for backward compatibility)
            # 1. Try Groq (Preferred - Fast & Free Tier)
            if settings.groq_api_key:
                api_key = SecretStr(settings.groq_api_key)
                self._llm = ChatGroq(
                    model=self.model_name,
                    temperature=self.temperature,
                    api_key=api_key,
                )
                return self._llm

            # 2. Try Hugging Face (Alternative)
            if settings.huggingface_api_key:
                try:
                    from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

                    # Use a good default if the Groq model name is passed
                    hf_model = "mistralai/Mistral-7B-Instruct-v0.3"
                    if "llama" in self.model_name.lower():
                        hf_model = "meta-llama/Meta-Llama-3-8B-Instruct"

                    llm = _make_hf_endpoint(
                        HuggingFaceEndpoint,
                        repo_id=hf_model,
                        task="text-generation",
                        max_new_tokens=512,
                        do_sample=False,
                        huggingfacehub_api_token=settings.huggingface_api_key,
                    )
                    self._llm = ChatHuggingFace(llm=llm)
                    return self._llm
                except ImportError:
                    self.logger.warning("langchain-huggingface not installed")
                except Exception as e:
                    self.logger.error(f"Failed to init Hugging Face LLM: {e}")

            # 3. No LLM configured
            raise LLMNotConfiguredError(
                "LLM is not configured. Set GROQ_API_KEY, GOOGLE_API_KEY, or HUGGINGFACE_API_KEY in your .env."
            )

        return self._llm

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt for this agent"""
        pass

    @abstractmethod
    async def process(self, state: AgentState) -> AgentState:
        """
        Process the current state and return updated state

        Args:
            state: Current workflow state

        Returns:
            Updated workflow state
        """
        pass

    def create_message(
        self,
        content: str,
        citations: Optional[list[Citation]] = None,
        confidence: float = 0.0,
        reasoning: Optional[str] = None,
    ) -> AgentMessage:
        """Create an agent message with metadata"""
        return AgentMessage(
            role=self.role,
            content=content,
            citations=citations or [],
            confidence=confidence,
            reasoning=reasoning,
        )

    async def invoke_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Invoke the LLM with the given prompt

        Args:
            prompt: User prompt
            system_prompt: Optional override for system prompt

        Returns:
            LLM response content
        """
        from langchain_core.messages import SystemMessage, HumanMessage

        messages = [
            SystemMessage(content=system_prompt or self.system_prompt),
            HumanMessage(content=prompt),
        ]

        self.logger.debug(f"Invoking LLM with prompt length: {len(prompt)}")

        response = await self.llm.ainvoke(messages)

        content: Any = response.content
        self.logger.debug(f"LLM response length: {len(str(content))}")

        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(part if isinstance(part, str) else str(part) for part in content)
        return str(content)

    def format_citations_for_prompt(self, citations: list[Citation]) -> str:
        """Format citations list for inclusion in prompts"""
        if not citations:
            return "No citations available."

        formatted = []
        for i, citation in enumerate(citations, 1):
            status_emoji = {
                "good_law": "🟢",
                "distinguished": "🟡",
                "overruled": "🔴",
            }.get(citation.status.value, "⚪")

            formatted.append(
                f"{i}. {status_emoji} {citation.formatted}\n"
                f"   Status: {citation.status.value.replace('_', ' ').title()}"
            )

        return "\n".join(formatted)

    def format_documents_for_prompt(self, documents: list[dict]) -> str:
        """Format document excerpts for inclusion in prompts"""
        if not documents:
            return "No documents available."

        formatted = []
        for i, doc in enumerate(documents, 1):
            content = doc.get("content", "") or ""
            excerpt = content[:500] + "..." if len(content) > 500 else content
            title = doc.get("title") or doc.get("case_title") or doc.get("document_title")
            if not title:
                title = doc.get("document_id") or doc.get("id") or "Unknown"
            court = doc.get("court") or doc.get("metadata", {}).get("court") or "Unknown"
            formatted.append(
                f"[Document {i}]\n"
                f"Id: {doc.get('id', 'N/A')}\n"
                f"DocumentId: {doc.get('document_id', 'N/A')}\n"
                f"Title: {title}\n"
                f"Court: {court}\n"
                f"Page: {doc.get('page_number', 'N/A')}, Para: {doc.get('paragraph_number', 'N/A')}\n"
                f"Content: {excerpt}\n"
            )

        return "\n---\n".join(formatted)
