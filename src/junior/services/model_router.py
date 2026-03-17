"""
Model Router - Central service for routing tasks to specialized LLMs

This service implements the Multi-Model Agentic AI architecture where each
task is routed to the best-in-class model for that specific purpose.

Supported Providers:
- Perplexity AI (Sonar-Pro) - For long-context research + online search
- Groq - For fast inference (Llama 3.3 70B)
- Hugging Face - Fallback for various models
"""

from typing import Optional, Literal, Any
from enum import Enum

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from pydantic import SecretStr

from junior.core import settings, get_logger
from junior.core.exceptions import LLMNotConfiguredError

logger = get_logger(__name__)


class ModelProvider(str, Enum):
    """Supported model providers"""
    PERPLEXITY = "perplexity"
    GROQ = "groq"
    HUGGINGFACE = "huggingface"
    OPENROUTER = "openrouter"


class ModelPurpose(str, Enum):
    """Purpose-specific model assignments"""
    RESEARCHER = "researcher"  # Long-context reading (Perplexity Sonar-Pro)
    CRITIC = "critic"  # Fast reasoning (Llama 3.3 70B)
    WRITER = "writer"  # Instruction following (Llama 3.3 70B)
    CHAT = "chat"  # Conversational AI (Perplexity Sonar-Pro)
    TRANSLATOR = "translator"  # Translation (OpenRouter / Qwen)
    GENERAL = "general"  # Fallback (Llama-3.3-70B)


class ModelRouter:
    """
    Routes LLM requests to the appropriate specialized model
    
    Each purpose (researcher, critic, writer, chat) uses a different model
    optimized for that specific task.
    """

    def __init__(self):
        self._model_cache: dict[str, BaseChatModel] = {}
        self.logger = get_logger(__name__)

    # Fallback chain: primary provider → Groq (always available) → error
    _GROQ_FALLBACK_MODEL = "llama-3.3-70b-versatile"

    def get_model(
        self,
        purpose: ModelPurpose = ModelPurpose.GENERAL,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
    ) -> BaseChatModel:
        """
        Get the appropriate LLM for the specified purpose.

        Implements a 3-tier smart fallback chain:
          Tier 1 — configured provider for *purpose* (Perplexity / OpenRouter / …)
          Tier 2 — Groq llama-3.3-70b-versatile (fast, almost always available)
          Tier 3 — raise LLMNotConfiguredError (all chains exhausted)

        Args:
            purpose: What the model will be used for
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens to generate

        Returns:
            Configured LangChain chat model

        Raises:
            LLMNotConfiguredError: If no API keys are configured for *any* provider
        """
        cache_key = f"{purpose.value}_{temperature}_{max_tokens}"

        if cache_key in self._model_cache:
            return self._model_cache[cache_key]

        # --- Tier 1: configured primary provider ---
        model_name, provider = self._get_model_config(purpose)
        try:
            model = self._create_model(
                provider=provider,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            self._model_cache[cache_key] = model
            self.logger.info(
                f"[ModelRouter] {purpose.value} → {model_name} ({provider.value}) [primary]"
            )
            return model
        except (LLMNotConfiguredError, ImportError, ValueError) as primary_err:
            self.logger.warning(
                f"[ModelRouter] Primary provider failed for {purpose.value} "
                f"({provider.value}/{model_name}): {primary_err}. Trying Groq fallback…"
            )

        # --- Tier 2: Groq fallback (already configured for this project) ---
        if provider != ModelProvider.GROQ:  # avoid infinite loop
            try:
                fallback_model = self._create_groq_model(
                    model_name=self._GROQ_FALLBACK_MODEL,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                self._model_cache[cache_key] = fallback_model
                self.logger.warning(
                    f"[ModelRouter] {purpose.value} → {self._GROQ_FALLBACK_MODEL} (groq) [tier-2 fallback]"
                )
                return fallback_model
            except (LLMNotConfiguredError, ImportError) as groq_err:
                self.logger.error(
                    f"[ModelRouter] Groq fallback also failed: {groq_err}"
                )

        # --- Tier 3: all chains exhausted ---
        raise LLMNotConfiguredError(
            f"No LLM provider is available for purpose '{purpose.value}'. "
            "Configure at least GROQ_API_KEY in your .env file."
        )

    def _get_model_config(self, purpose: ModelPurpose) -> tuple[str, ModelProvider]:
        """Get model name and provider for the specified purpose"""
        # Helper: safely resolve provider enum, defaulting to GROQ on bad values
        def _provider(name: str) -> ModelProvider:
            try:
                return ModelProvider(name)
            except ValueError:
                self.logger.warning(f"[ModelRouter] Unknown provider '{name}', defaulting to groq")
                return ModelProvider.GROQ

        config_map = {
            ModelPurpose.RESEARCHER: (
                settings.researcher_model,
                _provider(settings.researcher_provider),
            ),
            ModelPurpose.CRITIC: (
                settings.critic_model,
                _provider(settings.critic_provider),
            ),
            ModelPurpose.WRITER: (
                settings.writer_model,
                _provider(settings.writer_provider),
            ),
            ModelPurpose.CHAT: (
                settings.chat_model,
                _provider(settings.chat_provider),
            ),
            ModelPurpose.TRANSLATOR: (
                getattr(settings, "translator_model", "qwen/qwen-2.5-72b-instruct"),
                _provider(getattr(settings, "translator_provider", "openrouter")),
            ),
            ModelPurpose.GENERAL: (
                settings.default_llm_model,
                ModelProvider.GROQ,
            ),
        }

        return config_map.get(purpose, config_map[ModelPurpose.GENERAL])

    def _create_model(
        self,
        provider: ModelProvider,
        model_name: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> BaseChatModel:
        """Create a model instance for the specified provider"""

        if provider == ModelProvider.PERPLEXITY:
            return self._create_perplexity_model(model_name, temperature, max_tokens)
        elif provider == ModelProvider.GROQ:
            return self._create_groq_model(model_name, temperature, max_tokens)
        elif provider == ModelProvider.HUGGINGFACE:
            return self._create_huggingface_model(model_name, temperature, max_tokens)
        elif provider == ModelProvider.OPENROUTER:
            return self._create_openrouter_model(model_name, temperature, max_tokens)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _create_perplexity_model(
        self,
        model_name: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> BaseChatModel:
        """Create Perplexity AI model (Sonar-Pro with online search)"""
        if not settings.perplexity_api_key:
            raise LLMNotConfiguredError(
                "Perplexity AI is not configured. Set PERPLEXITY_API_KEY in your .env file.\n"
                "Get your API key at: https://www.perplexity.ai/settings/api"
            )
        
        try:
            from langchain_perplexity import ChatPerplexity
            
            return ChatPerplexity(
                model=model_name,
                pplx_api_key=settings.perplexity_api_key,
                temperature=temperature,
                max_tokens=max_tokens or 8192,
            )
        except ImportError:
            raise LLMNotConfiguredError(
                "langchain-perplexity is not installed. "
                "Run: pip install langchain-perplexity"
            )

    def _create_groq_model(
        self,
        model_name: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> BaseChatModel:
        """Create Groq model"""
        if not settings.groq_api_key:
            raise LLMNotConfiguredError(
                "Groq is not configured. Set GROQ_API_KEY in your .env file.\n"
                "Get your free API key at: https://console.groq.com/"
            )
        
        from langchain_groq import ChatGroq
        
        return ChatGroq(
            model=model_name,
            api_key=SecretStr(settings.groq_api_key),
            temperature=temperature,
            max_tokens=max_tokens or 8192,
        )

    def _create_openrouter_model(
        self,
        model_name: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> BaseChatModel:
        """Create an OpenRouter model (access 100+ models via OpenAI-compatible API)."""
        api_key = getattr(settings, "openrouter_api_key", "")
        if not api_key:
            raise LLMNotConfiguredError(
                "OpenRouter is not configured. Set OPENROUTER_API_KEY in your .env file.\n"
                "Get your free API key at: https://openrouter.ai/keys"
            )
        try:
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=model_name,
                api_key=SecretStr(api_key),
                base_url="https://openrouter.ai/api/v1",
                temperature=temperature,
                max_tokens=max_tokens or 4096,
                default_headers={
                    "HTTP-Referer": "https://github.com/junior-ai",
                    "X-Title": "Junior Legal AI",
                },
            )
        except ImportError:
            raise LLMNotConfiguredError(
                "langchain-openai is not installed. Run: pip install langchain-openai"
            )

    def _create_huggingface_model(
        self,
        model_name: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> BaseChatModel:
        """Create Hugging Face model"""
        if not settings.huggingface_api_key:
            raise LLMNotConfiguredError(
                "Hugging Face is not configured. Set HUGGINGFACE_API_KEY in your .env file.\n"
                "Get your free API key at: https://huggingface.co/settings/tokens"
            )
        
        try:
            from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
            
            # Create endpoint
            endpoint = HuggingFaceEndpoint(
                repo_id=model_name,
                task="text-generation",
                max_new_tokens=max_tokens or 512,
                temperature=temperature,
                huggingfacehub_api_token=settings.huggingface_api_key,
            )
            
            return ChatHuggingFace(llm=endpoint)
        except ImportError:
            raise LLMNotConfiguredError(
                "langchain-huggingface is not installed. "
                "Run: pip install langchain-huggingface"
            )

    async def invoke(
        self,
        purpose: ModelPurpose,
        messages: list[BaseMessage],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Convenience method to invoke a model and get string response
        
        Args:
            purpose: What the model will be used for
            messages: List of chat messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Model response as string
        """
        model = self.get_model(purpose, temperature, max_tokens)
        response = await model.ainvoke(messages)
        
        # Extract string content
        content: Any = response.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(str(part) for part in content)
        return str(content)

    def clear_cache(self):
        """Clear the model cache (useful for testing or reconfiguration)"""
        self._model_cache.clear()
        self.logger.info("Model cache cleared")


# Global router instance
_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    """Get or create the global model router instance"""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
