"""
Services for Junior Legal Assistant
Business logic and utility services
"""

from .embedding import EmbeddingService
from .pii_redactor import PIIRedactor
from .pdf_processor import PDFProcessor
from .translator import TranslationService
from .document_formatter import DocumentFormatter
from .judge_corpus import JudgeCorpusService, get_judge_corpus_service
from .audit_log import AuditEvent, append_audit_event, recent_audit_events, verify_audit_chain

__all__ = [
    "EmbeddingService",
    "PIIRedactor",
    "PDFProcessor",
    "TranslationService",
    "DocumentFormatter",
    "JudgeCorpusService",
    "get_judge_corpus_service",
    "AuditEvent",
    "append_audit_event",
    "recent_audit_events",
    "verify_audit_chain",
]
