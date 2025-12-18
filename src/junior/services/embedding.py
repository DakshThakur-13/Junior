"""
Embedding Service for vector similarity search
"""

from typing import Optional
from junior.core import settings, get_logger

logger = get_logger(__name__)

class EmbeddingService:
    """
    Service for generating text embeddings

    Uses Groq's embedding API or falls back to local models
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.embedding_model
        self._client = None

    @property
    def client(self):
        """Lazy-load the embedding client"""
        if self._client is None:
            from groq import Groq
            self._client = Groq(api_key=settings.groq_api_key)
        return self._client

    async def get_embedding(self, text: str) -> list[float]:
        """
        Get embedding vector for text

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        logger.debug(f"Generating embedding for text of length {len(text)}")

        # Truncate if too long (most models have a limit)
        max_length = 8000
        if len(text) > max_length:
            text = text[:max_length]
            logger.warning(f"Text truncated to {max_length} characters for embedding")

        try:
            # Using Groq/OpenAI compatible API
            # Note: Groq may not have embedding API, using placeholder
            embedding = await self._get_embedding_from_api(text)
            return embedding
        except Exception as e:
            logger.error(f"Embedding API error: {e}")
            # Fallback to simple hash-based embedding (for testing)
            return self._fallback_embedding(text)

    async def _get_embedding_from_api(self, text: str) -> list[float]:
        """
        Get embedding from API (Hugging Face or Groq)
        """
        # 1. Try Hugging Face Inference API (optional)
        if settings.huggingface_api_key:
            try:
                from langchain_huggingface import HuggingFaceEndpointEmbeddings

                embeddings = HuggingFaceEndpointEmbeddings(
                    model=self.model_name,
                    task="feature-extraction",
                    huggingfacehub_api_token=settings.huggingface_api_key,
                )
                return await embeddings.aembed_query(text)
            except Exception as e:
                logger.warning(f"Hugging Face embedding failed: {e}")

        # 2. Try Groq (if supported model)
        if settings.groq_api_key:
            try:
                # Note: Check if Groq supports embeddings in your region/model
                # This is a placeholder for Groq's future embedding support
                pass
            except Exception:
                pass

        # 3. Fallback to local sentence-transformers (free)
        # NOTE: This may trigger a model download. Guard behind a setting so
        # deployments in restricted networks don't hang on repeated retries.
        if getattr(settings, "allow_hf_model_downloads", False):
            try:
                from langchain_huggingface import HuggingFaceEmbeddings

                embeddings = HuggingFaceEmbeddings(model_name=self.model_name)
                return await embeddings.aembed_query(text)
            except ImportError:
                logger.warning("sentence-transformers not installed for local embeddings")
            except Exception as e:
                logger.warning(f"Local embedding failed: {e}")
        else:
            logger.info("Skipping local HF embeddings (allow_hf_model_downloads=false)")

        # 4. Last Resort: Deterministic fallback (testing only)
        logger.warning("Using fallback embeddings (testing only)")
        return self._fallback_embedding(text)

    def _fallback_embedding(self, text: str) -> list[float]:
        """
        Fallback embedding using simple hash

        Only for testing - not suitable for production
        """
        import hashlib
        import numpy as np

        # Create deterministic embedding from text hash
        hash_bytes = hashlib.sha512(text.encode()).digest()

        # Expand to 1536 dimensions
        np.random.seed(int.from_bytes(hash_bytes[:4], 'big'))
        embedding = np.random.randn(1536).tolist()

        # Normalize
        norm = np.linalg.norm(embedding)
        embedding = [x / norm for x in embedding]

        logger.warning("Using fallback embedding - not suitable for production")
        return embedding

    async def get_batch_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Get embeddings for multiple texts

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = await self.get_embedding(text)
            embeddings.append(embedding)
        return embeddings

    def cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """
        Calculate cosine similarity between two vectors

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity (0-1)
        """
        import numpy as np

        v1 = np.array(vec1)
        v2 = np.array(vec2)

        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))
