"""Local on-disk store for documents/chunks (dev-friendly RAG fallback).

Why this exists:
- Supabase is optional in this project.
- The upload pipeline currently processes PDFs but (by default) does not persist
  documents/chunks into Supabase.
- Agentic RAG needs *some* retrieval source; this store provides a lightweight,
  dependency-free option.

Storage layout (under uploads/):
- uploads/documents/{document_id}.json  (document metadata)
- uploads/chunks/{document_id}.jsonl    (one JSON chunk per line; includes embedding)

This is not meant to be a high-performance vector DB.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Optional

from junior.core import get_logger
from junior.core.types import DocumentChunk, LegalDocument

logger = get_logger(__name__)

_WORD_RE = re.compile(r"[A-Za-z0-9_]+", re.UNICODE)

def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _WORD_RE.findall(text or "") if t]

def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return float(dot / (math.sqrt(na) * math.sqrt(nb)))

class LocalDocumentStore:
    def __init__(self, base_dir: Path | str = Path("uploads")):
        self.base_dir = Path(base_dir)
        self.docs_dir = self.base_dir / "documents"
        self.chunks_dir = self.base_dir / "chunks"
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_dir.mkdir(parents=True, exist_ok=True)

    def save_document(self, document: LegalDocument) -> None:
        path = self.docs_dir / f"{document.id}.json"
        # Use Pydantic's JSON mode so datetimes and other types serialize safely.
        data = document.model_dump(mode="json")
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def save_chunks(self, document_id: str, chunks: Iterable[DocumentChunk]) -> None:
        path = self.chunks_dir / f"{document_id}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(json.dumps(chunk.model_dump(mode="json"), ensure_ascii=False))
                f.write("\n")

    def load_document(self, document_id: str) -> Optional[dict[str, Any]]:
        path = self.docs_dir / f"{document_id}.json"
        if not path.exists():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except Exception as e:
            logger.warning(f"Failed to read local document {document_id}: {e}")
            return None

    def load_chunks(self, document_id: str) -> list[dict[str, Any]]:
        """Load all chunks for a given document_id from local storage."""
        path = self.chunks_dir / f"{document_id}.jsonl"
        if not path.exists():
            return []
        chunks: list[dict[str, Any]] = []
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if isinstance(obj, dict):
                            chunks.append(obj)
                    except Exception:
                        continue
        except Exception as e:
            logger.warning(f"Failed to read local chunks for {document_id}: {e}")
            return []
        return chunks

    def iter_chunks(self) -> Iterable[dict[str, Any]]:
        if not self.chunks_dir.exists():
            return []
        for file in self.chunks_dir.glob("*.jsonl"):
            try:
                with file.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            if isinstance(obj, dict):
                                yield obj
                        except Exception:
                            continue
            except Exception:
                continue

    def search_hybrid(
        self,
        query: str,
        query_embedding: Optional[list[float]],
        limit: int = 10,
        bm25_weight: float = 0.35,
        vector_weight: float = 0.65,
    ) -> list[tuple[dict[str, Any], float]]:
        """Hybrid retrieval: BM25-ish + cosine similarity.

        - If `query_embedding` is None, falls back to BM25-only.
        - Returns list of (chunk_dict, score) sorted descending.
        """
        chunks = list(self.iter_chunks())
        if not chunks:
            return []

        q_tokens = _tokenize(query)
        if not q_tokens:
            return []

        # Build document frequencies for BM25.
        doc_tokens: list[list[str]] = []
        df: dict[str, int] = {}
        doc_lens: list[int] = []
        for ch in chunks:
            toks = _tokenize(str(ch.get("content") or ""))
            doc_tokens.append(toks)
            doc_lens.append(len(toks))
            for t in set(toks):
                df[t] = df.get(t, 0) + 1

        n_docs = len(chunks)
        avgdl = (sum(doc_lens) / n_docs) if n_docs else 1.0

        def bm25_score(idx: int) -> float:
            k1 = 1.2
            b = 0.75
            toks = doc_tokens[idx]
            if not toks:
                return 0.0
            tf: dict[str, int] = {}
            for t in toks:
                tf[t] = tf.get(t, 0) + 1

            score = 0.0
            dl = doc_lens[idx]
            for t in q_tokens:
                if t not in tf:
                    continue
                # idf with +1 smoothing
                n_q = df.get(t, 0)
                idf = math.log(1.0 + (n_docs - n_q + 0.5) / (n_q + 0.5))
                freq = tf[t]
                denom = freq + k1 * (1.0 - b + b * (dl / avgdl))
                score += idf * (freq * (k1 + 1.0) / (denom or 1.0))
            return score

        bm25_scores = [bm25_score(i) for i in range(n_docs)]
        bm25_max = max(bm25_scores) if bm25_scores else 0.0

        results: list[tuple[dict[str, Any], float]] = []
        for i, ch in enumerate(chunks):
            bm25_norm = (bm25_scores[i] / bm25_max) if bm25_max > 0 else 0.0

            vec_score = 0.0
            if query_embedding is not None:
                emb = ch.get("embedding")
                if isinstance(emb, list) and emb and all(isinstance(x, (int, float)) for x in emb):
                    vec_score = _cosine(query_embedding, emb)

            if query_embedding is None:
                score = bm25_norm
            else:
                score = (bm25_weight * bm25_norm) + (vector_weight * vec_score)

            results.append((ch, float(score)))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

def rerank_with_cross_encoder(
    query: str,
    candidates: list[tuple[dict[str, Any], float]],
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    top_k: int = 10,
) -> list[tuple[dict[str, Any], float]]:
    """Optional reranker using sentence-transformers CrossEncoder.

    If sentence-transformers isn't available, returns input unchanged.
    """
    try:
        from sentence_transformers import CrossEncoder  # type: ignore
    except Exception:
        return candidates[:top_k]

    if not candidates:
        return []

    texts = [str(c[0].get("content") or "") for c in candidates]
    pairs = [(query, t) for t in texts]

    try:
        reranker = CrossEncoder(model_name)
        scores = reranker.predict(pairs)
    except Exception as e:
        logger.warning(f"Cross-encoder rerank failed: {e}")
        return candidates[:top_k]

    enriched: list[tuple[dict[str, Any], float]] = []
    for (chunk, _base_score), s in zip(candidates, scores):
        try:
            enriched.append((chunk, float(s)))
        except Exception:
            enriched.append((chunk, 0.0))

    enriched.sort(key=lambda x: x[1], reverse=True)
    return enriched[:top_k]
