"""
Database repositories for data access
"""

from datetime import datetime
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


def _token_count(text: str) -> int:
    return len((text or "").split())


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
        data = {
            "id": document_id,
            "title": document.title,
            # Supabase schema uses enum-like names (e.g. SUPREME_COURT)
            "court": document.court.name,
            "case_number": document.case_number,
            # Supabase schema uses judgment_date (DATE), not date (TIMESTAMP)
            "judgment_date": document.date.date().isoformat(),
            "judges": document.judges,
            "parties": document.parties,
            "summary": document.summary,
            "full_text": document.full_text,
            # Supabase schema uses legal_status + language enum-like names
            "legal_status": document.status.name,
            "language": document.language.name,
            "metadata": document.metadata,
            "created_at": datetime.utcnow().isoformat(),
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
            else datetime.utcnow()
        )

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
            metadata=cast(dict[str, Any], doc_data.get("metadata") or {}),
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

        # Using Supabase's pgvector for similarity search
        query = self.db.client.rpc(
            "match_document_chunks",
            {
                # Supabase RPC can accept a JSON array for vector casting.
                "query_embedding": embedding,
                "match_threshold": threshold,
                "match_count": limit,
            }
        )
        
        if court_filter:
            courts = [c.name for c in court_filter]
            # Note: Filtering would be handled in the RPC function
        
        result = query.execute()
        
        chunks = []
        rows = cast(list[dict[str, Any]], result.data or [])
        for row in rows:
            chunk = DocumentChunk(
                id=str(row["id"]),
                document_id=str(row["document_id"]),
                content=str(row["content"]),
                page_number=int(row["page_number"]),
                paragraph_number=cast(Optional[int], row.get("paragraph_number")),
                metadata=cast(dict[str, Any], row.get("metadata") or {}),
            )
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
            "created_at": datetime.utcnow().isoformat(),
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
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
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
            "created_at": datetime.utcnow().isoformat(),
        }
        
        self.db.chat_messages.insert(data).execute()
        
        # Update session's updated_at
        self.db.chat_sessions.update(
            {"updated_at": datetime.utcnow().isoformat()}
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
            "preferred_language": preferred_language.value,
            "settings": {},
            "created_at": datetime.utcnow().isoformat(),
        }
        
        self.db.users.insert(data).execute()
        logger.info(f"Created user: {user_id}")
        return data
    
    async def update_settings(self, user_id: str, settings: dict[str, Any]) -> dict[str, Any]:
        """Update user settings"""
        result = self.db.users.update(
            {"settings": settings, "updated_at": datetime.utcnow().isoformat()}
        ).eq("id", user_id).execute()
        
        data_list = cast(list[dict[str, Any]], result.data or [])
        return data_list[0] if data_list else {}
