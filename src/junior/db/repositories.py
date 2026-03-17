"""Database repositories for data access."""

from datetime import datetime, timezone
import re
from typing import Any, Optional, TypeVar, cast
from uuid import uuid4

from junior.core import get_logger
from junior.core.types import (
    LegalDocument,
    DocumentChunk,
    Court,
    CaseStatus,
    Language,
)
from .client import SupabaseClient, get_supabase_client

logger = get_logger(__name__)

TEnum = TypeVar("TEnum")


def _copy_model(model: Any, *, update: dict[str, Any]):
    copier = getattr(model, "model_copy", None)
    if callable(copier):
        return copier(update=update)
    copier = getattr(model, "copy", None)
    if callable(copier):
        return copier(update=update)
    raise TypeError("Unsupported model type: expected a Pydantic model")


def _parse_enum(enum_cls: Any, raw: Any, *, default: Any) -> Any:
    if raw is None:
        return default

    value = str(raw)
    if hasattr(enum_cls, "__members__") and value in enum_cls.__members__:
        return enum_cls[value]

    try:
        return enum_cls(value)
    except Exception:
        pass

    normalized = value.strip()
    if hasattr(enum_cls, "__members__"):
        upper = normalized.upper()
        if upper in enum_cls.__members__:
            return enum_cls[upper]

    try:
        return enum_cls(normalized.lower())
    except Exception:
        return default


def _vector_literal(vec: Optional[list[float]]) -> Optional[str]:
    """Format embeddings for Supabase pgvector columns.

    PostgREST accepts pgvector values as a string literal like "[1,2,3]".
    Using a literal is more portable than sending a JSON array.
    """
    if vec is None:
        return None
    if not isinstance(vec, list) or not vec:
        return "[]"
    return "[" + ",".join(str(float(x)) for x in vec) + "]"


def _resize_embedding(vec: list[float], target_dim: int) -> list[float]:
    if target_dim <= 0:
        return vec
    if len(vec) == target_dim:
        return vec
    if len(vec) > target_dim:
        return vec[:target_dim]
    return vec + [0.0] * (target_dim - len(vec))


def _extract_mismatch_dims(message: str) -> Optional[tuple[int, int]]:
    m = re.search(r"different vector dimensions\s+(\d+)\s+and\s+(\d+)", message, re.IGNORECASE)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _token_count(text: str) -> int:
    return len((text or "").split())


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BaseRepository:
    """Base repository with common functionality"""
    
    def __init__(self, client: Optional[SupabaseClient] = None):
        self._client = client or get_supabase_client()
    
    @property
    def db(self) -> SupabaseClient:
        return self._client


class DocumentRepository(BaseRepository):
    """Repository for legal documents"""
    
    async def create(self, document: LegalDocument) -> LegalDocument:
        """Create a new document"""
        document_id = (document.id or "").strip() or str(uuid4())
        metadata = cast(dict[str, Any], document.metadata or {})
        data = {
            "id": document_id,
            "title": document.title,
            "court": document.court.name,
            "case_number": document.case_number,
            "judgment_date": document.date.date().isoformat(),
            "judges": document.judges,
            "parties": document.parties,
            "summary": document.summary,
            "full_text": document.full_text,
            "legal_status": document.status.name,
            "language": document.language.name,
            "case_type": metadata.get("case_type"),
            "filing_date": metadata.get("filing_date"),
            "headnotes": metadata.get("headnotes"),
            "source_url": metadata.get("source_url"),
            "pdf_url": metadata.get("pdf_url"),
            "doc_hash": metadata.get("doc_hash"),
            "keywords": metadata.get("keywords") or [],
            "legal_provisions": metadata.get("legal_provisions") or [],
            "metadata": metadata,
            "created_at": _utcnow_iso(),
            "updated_at": _utcnow_iso(),
        }

        # Use upsert so re-ingestion refreshes metadata instead of duplicating.
        self.db.documents.upsert(data, on_conflict="id").execute()
        logger.info(f"Created/updated document: {document_id}")
        return _copy_model(document, update={"id": document_id})
    
    async def get_by_id(self, document_id: str) -> Optional[LegalDocument]:
        """Get document by ID"""
        result = self.db.documents.select("*").eq("id", document_id).execute()
        
        if not result.data:
            return None
        
        data_list = cast(list[dict[str, Any]], result.data or [])
        doc_data = data_list[0]

        raw_date = doc_data.get("judgment_date") or doc_data.get("date")
        doc_date = (
            datetime.fromisoformat(str(raw_date))
            if raw_date is not None
            else datetime.now(timezone.utc)
        )

        metadata = cast(dict[str, Any], doc_data.get("metadata") or {})
        metadata = {
            **metadata,
            "case_type": doc_data.get("case_type"),
            "filing_date": doc_data.get("filing_date"),
            "headnotes": doc_data.get("headnotes"),
            "source_url": doc_data.get("source_url"),
            "pdf_url": doc_data.get("pdf_url"),
            "doc_hash": doc_data.get("doc_hash"),
            "keywords": doc_data.get("keywords") or [],
            "legal_provisions": doc_data.get("legal_provisions") or [],
            "view_count": doc_data.get("view_count", 0),
            "is_landmark": doc_data.get("is_landmark", False),
        }

        return LegalDocument(
            id=str(doc_data["id"]),
            title=str(doc_data["title"]),
            court=_parse_enum(Court, doc_data.get("court"), default=Court.OTHER),
            case_number=str(doc_data["case_number"]),
            date=doc_date,
            judges=cast(list[str], doc_data.get("judges") or []),
            parties=cast(dict[str, Any], doc_data.get("parties") or {}),
            summary=cast(Optional[str], doc_data.get("summary")),
            full_text=cast(Optional[str], doc_data.get("full_text")),
            status=_parse_enum(
                CaseStatus,
                doc_data.get("legal_status") or doc_data.get("status"),
                default=CaseStatus.GOOD_LAW,
            ),
            language=_parse_enum(Language, doc_data.get("language"), default=Language.ENGLISH),
            metadata=metadata,
        )
    
    async def search_by_embedding(
        self,
        embedding: list[float],
        limit: int = 10,
        court_filter: Optional[list[Court]] = None,
        threshold: float = 0.7,
    ) -> list[tuple[DocumentChunk, float]]:
        """Search documents using vector similarity"""
        if not embedding:
            raise ValueError("Embedding must be a non-empty vector")

        params = {
            "query_embedding": embedding,
            "match_threshold": threshold,
            "match_count": limit,
            "filter_courts": [c.name for c in court_filter] if court_filter else None,
        }

        try:
            result = self.db.client.rpc("match_document_chunks", params).execute()
        except Exception as exc:
            msg = str(exc)
            dims = _extract_mismatch_dims(msg)
            if not dims:
                raise

            db_dim, query_dim = dims
            logger.warning(
                f"Vector mismatch in Supabase search (db={db_dim}, query={query_dim}). Retrying with resized query embedding."
            )

            resized = _resize_embedding(embedding, db_dim)
            params["query_embedding"] = resized
            result = self.db.client.rpc("match_document_chunks", params).execute()
        
        chunks = []
        rows = cast(list[dict[str, Any]], result.data or [])
        for row in rows:
            chunk = DocumentChunk(
                id=str(row.get("id") or row.get("chunk_id")),
                document_id=str(row["document_id"]),
                content=str(row["content"]),
                page_number=int(row.get("page_number") or 1),
                paragraph_number=cast(Optional[int], row.get("paragraph_number")),
                metadata=cast(dict[str, Any], row.get("metadata") or {}),
            )
            chunk.metadata.setdefault("title", row.get("title") or row.get("document_title") or "Unknown")
            chunk.metadata.setdefault("case_number", row.get("case_number"))
            chunk.metadata.setdefault("court", row.get("court"))
            chunk.metadata.setdefault("judgment_date", row.get("judgment_date"))
            chunks.append((chunk, float(row["similarity"])))
        
        return chunks
    
    async def save_chunk(self, chunk: DocumentChunk) -> DocumentChunk:
        """Save a document chunk with embedding"""
        chunk_id = (chunk.id or "").strip() or str(uuid4())

        chunk_type = (
            cast(Optional[str], (chunk.metadata or {}).get("chunk_type"))
            or cast(Optional[str], (chunk.metadata or {}).get("source"))
            or "paragraph"
        )
        token_count = cast(Optional[int], (chunk.metadata or {}).get("token_count"))
        if token_count is None:
            token_count = _token_count(chunk.content)

        data = {
            "id": chunk_id,
            "document_id": chunk.document_id,
            "chunk_type": chunk_type,
            "content": chunk.content,
            "page_number": chunk.page_number,
            "paragraph_number": chunk.paragraph_number,
            "token_count": token_count,
            "embedding": _vector_literal(chunk.embedding),
            "metadata": chunk.metadata,
            "created_at": _utcnow_iso(),
        }

        # Upsert so re-ingestion fills missing embeddings instead of duplicating.
        self.db.document_chunks.upsert(data, on_conflict="id").execute()
        return _copy_model(chunk, update={"id": chunk_id})


class ChatRepository(BaseRepository):
    """Repository for chat sessions and messages"""
    
    async def create_session(self, user_id: str, title: Optional[str] = None) -> dict[str, Any]:
        """Create a new chat session"""
        session_id = str(uuid4())
        data = {
            "id": session_id,
            "user_id": user_id,
            "title": title or "New Research Session",
            "created_at": _utcnow_iso(),
            "updated_at": _utcnow_iso(),
        }
        
        self.db.chat_sessions.insert(data).execute()
        logger.info(f"Created chat session: {session_id}")
        return data
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        citations: Optional[list[dict]] = None,
        metadata: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Add a message to a chat session"""
        message_id = str(uuid4())
        data = {
            "id": message_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "citations": citations or [],
            "metadata": metadata or {},
            "translations": {},
            "token_count": _token_count(content),
            "created_at": _utcnow_iso(),
        }
        
        self.db.chat_messages.insert(data).execute()
        
        # Update session's updated_at
        self.db.chat_sessions.update(
            {"updated_at": _utcnow_iso()}
        ).eq("id", session_id).execute()
        
        return data
    
    async def get_session_messages(self, session_id: str) -> list[dict[str, Any]]:
        """Get all messages in a session"""
        result = self.db.chat_messages.select("*").eq(
            "session_id", session_id
        ).order("created_at").execute()
        
        return cast(list[dict[str, Any]], result.data or [])
    
    async def get_user_sessions(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent sessions for a user"""
        result = self.db.chat_sessions.select("*").eq(
            "user_id", user_id
        ).order("updated_at", desc=True).limit(limit).execute()
        
        return cast(list[dict[str, Any]], result.data or [])


class UserRepository(BaseRepository):
    """Repository for user management"""
    
    async def get_by_id(self, user_id: str) -> Optional[dict[str, Any]]:
        """Get user by ID"""
        result = self.db.users.select("*").eq("id", user_id).execute()
        data_list = cast(list[dict[str, Any]], result.data or [])
        return data_list[0] if data_list else None
    
    async def create(
        self,
        email: str,
        name: str,
        preferred_language: Language = Language.ENGLISH,
    ) -> dict[str, Any]:
        """Create a new user"""
        user_id = str(uuid4())
        data = {
            "id": user_id,
            "email": email,
            "name": name,
            "preferred_language": preferred_language.name,
            "settings": {},
            "created_at": _utcnow_iso(),
            "updated_at": _utcnow_iso(),
        }
        
        self.db.users.insert(data).execute()
        logger.info(f"Created user: {user_id}")
        return data
    
    async def update_settings(self, user_id: str, settings: dict[str, Any]) -> dict[str, Any]:
        """Update user settings"""
        result = self.db.users.update(
            {"settings": settings, "updated_at": _utcnow_iso()}
        ).eq("id", user_id).execute()
        
        data_list = cast(list[dict[str, Any]], result.data or [])
        return data_list[0] if data_list else {}
