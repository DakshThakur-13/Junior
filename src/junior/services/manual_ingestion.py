"""Manual ingestion (RAG "training") service.

Goal:
- Ingest publicly available PDFs (manuals, bare acts, guides) into the local RAG store.
- This is *not* model fine-tuning. It is Retrieval-Augmented Generation (RAG):
  the assistant retrieves chunks from ingested manuals and uses them as grounded context.

Safety:
- By default, ingestion only allows catalog items (no arbitrary URLs).
- Optional URL ingestion can be enabled via settings and domain allowlist.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

from junior.core import get_logger, settings
from junior.core.types import Court, LegalDocument
from junior.services.embedding import EmbeddingService
from junior.services.local_store import LocalDocumentStore
from junior.services.pdf_processor import PDFProcessor

logger = get_logger(__name__)

@dataclass(frozen=True)
class IngestResult:
    document_id: str
    title: str
    chunks: int
    bytes_downloaded: int
    source_url: str

def _safe_filename(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return digest

class ManualIngestionService:
    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.embedding_service = EmbeddingService()
        self.store = LocalDocumentStore(Path("uploads"))
        self.manuals_dir = Path(getattr(settings, "manuals_download_dir", "uploads/manuals"))
        self.manuals_dir.mkdir(parents=True, exist_ok=True)

    async def ingest_catalog_source(self, source_id: str, *, force: bool = False) -> IngestResult:
        from junior.services.official_sources import get_source_by_id

        item = get_source_by_id(source_id)
        if item is None:
            raise ValueError(f"Unknown source_id: {source_id}")

        url = (item.url or "").strip()
        if not url:
            raise ValueError("Selected source has no URL")

        return await self.ingest_pdf_url(
            url=url,
            title=item.title,
            metadata={
                "source_id": item.id,
                "source_url": item.url,
                "authority": item.authority,
                "publisher": item.publisher,
                "type": item.type,
                "tags": item.tags,
            },
            force=force,
            allow_arbitrary_url=False,
        )

    async def ingest_pdf_url(
        self,
        *,
        url: str,
        title: str,
        metadata: Optional[dict] = None,
        force: bool = False,
        allow_arbitrary_url: bool = False,
    ) -> IngestResult:
        """Download a PDF and index it into the local store."""

        url = (url or "").strip()
        if not url.lower().startswith("https://"):
            raise ValueError("Only https:// URLs are allowed")

        if not allow_arbitrary_url:
            # Catalog-only mode (default)
            if not metadata or not metadata.get("source_id"):
                raise ValueError("Direct URL ingestion is disabled. Use a catalog source_id.")
        else:
            if not getattr(settings, "manuals_allow_url_ingest", False):
                raise ValueError("Direct URL ingestion is disabled by configuration")

            allowlist = {
                d.strip().lower()
                for d in str(getattr(settings, "manuals_allowlist_domains", "")).split(",")
                if d.strip()
            }
            if allowlist:
                host = httpx.URL(url).host
                if not host or host.lower() not in allowlist:
                    raise ValueError("URL host is not in allowlist")

        # If we have already ingested this URL, reuse doc id unless forced.
        url_key = _safe_filename(url)
        document_id = f"manual_{url_key}"

        if not force:
            existing = self.store.load_document(document_id)
            if existing:
                chunks = len(self.store.load_chunks(document_id))
                return IngestResult(
                    document_id=document_id,
                    title=str(existing.get("title") or title),
                    chunks=chunks,
                    bytes_downloaded=0,
                    source_url=url,
                )

        max_bytes = int(getattr(settings, "manuals_max_bytes", 50_000_000))

        pdf_path = self.manuals_dir / f"{document_id}.pdf"
        bytes_downloaded = 0

        # Download with streaming & size cap
        logger.info(f"Downloading manual PDF: {url}")
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                content_type = (resp.headers.get("content-type") or "").lower()
                if "pdf" not in content_type and not url.lower().endswith(".pdf"):
                    raise ValueError("URL does not look like a PDF (content-type not pdf)")

                with pdf_path.open("wb") as f:
                    async for chunk in resp.aiter_bytes():
                        if not chunk:
                            continue
                        bytes_downloaded += len(chunk)
                        if bytes_downloaded > max_bytes:
                            raise ValueError("PDF exceeds maximum allowed size")
                        f.write(chunk)

        # Process PDF into chunks
        document, chunks = self.pdf_processor.process_pdf(pdf_path, document_id=document_id)

        # Override title/metadata for manuals
        document = LegalDocument(
            **{
                **document.model_dump(),
                "title": title or document.title,
                "court": Court.OTHER,
                "case_number": "MANUAL",
                "metadata": {**(document.metadata or {}), **(metadata or {}), "category": "manual"},
            }
        )

        # Embed and persist
        for ch in chunks:
            ch.embedding = await self.embedding_service.get_embedding(ch.content)

        self.store.save_document(document)
        self.store.save_chunks(document_id, chunks)

        # Optional: persist to Supabase too
        if settings.supabase_url and settings.supabase_key:
            try:
                from junior.db import DocumentRepository

                repo = DocumentRepository()
                await repo.create(document)
                for ch in chunks:
                    await repo.save_chunk(ch)
            except Exception as e:
                logger.warning(f"Supabase manual persistence failed (local store still available): {e}")

        return IngestResult(
            document_id=document_id,
            title=document.title,
            chunks=len(chunks),
            bytes_downloaded=bytes_downloaded,
            source_url=url,
        )
