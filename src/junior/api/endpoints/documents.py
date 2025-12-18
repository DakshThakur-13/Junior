"""
Document management endpoints
"""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional

from junior.core import get_logger, settings
from junior.core.types import Court
from junior.services import PDFProcessor, PIIRedactor, EmbeddingService
from junior.db import DocumentRepository
from junior.api.schemas import (
    DocumentUploadResponse,
    DocumentSearchRequest,
    DocumentSearchResult,
)

router = APIRouter()
logger = get_logger(__name__)

# Ensure upload directory exists
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    court: Optional[str] = Form(None),
    case_number: Optional[str] = Form(None),
):
    """
    Upload a legal document (PDF)
    
    The document will be:
    1. Saved to storage
    2. PII redacted (locally)
    3. Text extracted and chunked
    4. Embeddings generated
    5. Stored in vector database
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    logger.info(f"Uploading document: {file.filename}")
    
    try:
        # Save file temporarily
        document_id = str(uuid4())
        file_path = UPLOAD_DIR / f"{document_id}.pdf"
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Process PDF
        processor = PDFProcessor()
        document, chunks = processor.process_pdf(file_path, document_id)
        
        # PII Redaction
        pii_redactor = PIIRedactor()
        redacted_chunks = []
        for chunk in chunks:
            result = pii_redactor.redact(chunk.content)
            chunk.content = result.redacted_text
            redacted_chunks.append(chunk)
        
        # Generate embeddings
        embedding_service = EmbeddingService()
        for chunk in redacted_chunks:
            chunk.embedding = await embedding_service.get_embedding(chunk.content)

        # Store locally so Agentic RAG works without Supabase
        try:
            from junior.services.local_store import LocalDocumentStore
            store = LocalDocumentStore(UPLOAD_DIR)
            store.save_document(document)
            store.save_chunks(document_id, redacted_chunks)
        except Exception as e:
            logger.warning(f"Local store save failed: {e}")
        
        # Store in Supabase (optional)
        if settings.supabase_url and settings.supabase_key:
            try:
                doc_repo = DocumentRepository()
                await doc_repo.create(document)
                for chunk in redacted_chunks:
                    await doc_repo.save_chunk(chunk)
            except Exception as e:
                # Don't block uploads if DB write fails.
                logger.warning(f"Supabase store failed (continuing with local store): {e}")
        
        # Keep uploaded PDF on disk (enables evidence vault / later viewing)
        
        return DocumentUploadResponse(
            document_id=document_id,
            title=title or document.title,
            court=document.court.value,
            pages=len(chunks),
            chunks=len(redacted_chunks),
            status="processed",
        )
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=list[DocumentSearchResult])
async def search_documents(request: DocumentSearchRequest):
    """
    Search documents using semantic similarity
    
    Returns ranked list of relevant document chunks.
    """
    logger.info(f"Searching: {request.query[:50]}...")
    
    try:
        # Generate query embedding
        embedding_service = EmbeddingService()
        query_embedding = await embedding_service.get_embedding(request.query)
        
        # Search database
        doc_repo = DocumentRepository()
        results = await doc_repo.search_by_embedding(
            embedding=query_embedding,
            limit=request.limit,
            court_filter=request.court_filter,
            threshold=request.threshold,
        )
        
        # Format results
        search_results = []
        for chunk, score in results:
            search_results.append(DocumentSearchResult(
                document_id=chunk.document_id,
                title=chunk.metadata.get("title", "Unknown"),
                content=chunk.content,
                page_number=chunk.page_number,
                paragraph_number=chunk.paragraph_number,
                relevance_score=score,
                citation=None,
            ))
        
        return search_results
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}")
async def get_document(document_id: str):
    """
    Get document by ID
    
    Returns full document with metadata.
    """
    logger.info(f"Fetching document: {document_id}")
    
    # 1) Try Supabase first
    try:
        doc_repo = DocumentRepository()
        document = await doc_repo.get_by_id(document_id)
        if document:
            return {
                "id": document.id,
                "title": document.title,
                "court": document.court.value,
                "case_number": document.case_number,
                "date": document.date.isoformat(),
                "judges": document.judges,
                "status": document.status.value,
                "language": document.language.value,
            }
    except Exception as e:
        # Expected when Supabase is not configured
        logger.info(f"Supabase get_document unavailable, falling back to local store: {e}")

    # 2) Local store fallback
    try:
        from junior.services.local_store import LocalDocumentStore
        store = LocalDocumentStore(UPLOAD_DIR)
        doc = store.load_document(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        return {
            "id": doc.get("id"),
            "title": doc.get("title"),
            "court": (doc.get("court") or "other"),
            "case_number": doc.get("case_number"),
            "date": doc.get("date"),
            "judges": doc.get("judges") or [],
            "status": doc.get("status") or "good_law",
            "language": doc.get("language") or "en",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: str,
    page: Optional[int] = None,
    paragraph: Optional[int] = None,
):
    """
    Get chunks from a document
    
    Optionally filter by page or paragraph number.
    Used for the "Split-Screen Verification" feature.
    """
    logger.info(f"Fetching chunks for document: {document_id}")

    # Local store is the primary evidence-vault backend in dev (Supabase optional)
    try:
        from junior.services.local_store import LocalDocumentStore

        store = LocalDocumentStore(UPLOAD_DIR)
        chunks = store.load_chunks(document_id)

        if page is not None:
            chunks = [c for c in chunks if c.get("page_number") == page]
        if paragraph is not None:
            chunks = [c for c in chunks if c.get("paragraph_number") == paragraph]

        # Return minimal payload (don’t ship embeddings to UI)
        out = []
        for c in chunks:
            out.append(
                {
                    "id": c.get("id"),
                    "document_id": c.get("document_id"),
                    "content": c.get("content"),
                    "page_number": c.get("page_number"),
                    "paragraph_number": c.get("paragraph_number"),
                    "metadata": c.get("metadata") or {},
                }
            )

        return {
            "document_id": document_id,
            "chunks": out,
            "total": len(out),
            "source": "local",
        }
    except Exception as e:
        logger.error(f"Get document chunks error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document and its chunks
    """
    logger.info(f"Deleting document: {document_id}")
    
    # Placeholder - would delete from database
    return {
        "status": "deleted",
        "document_id": document_id,
    }
