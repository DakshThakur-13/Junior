"""
Custom exceptions for Junior application
"""

from typing import Optional

class JuniorException(Exception):
    """Base exception for Junior application"""

    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code or "JUNIOR_ERROR"
        super().__init__(self.message)

class ConfigurationError(JuniorException):
    """Configuration related errors"""

    def __init__(self, message: str):
        super().__init__(message, code="CONFIG_ERROR")

class LLMNotConfiguredError(ConfigurationError):
    """Raised when LLM features are invoked without required configuration"""

    def __init__(self, message: str = "GROQ_API_KEY is not configured"):
        super().__init__(message)

class DatabaseError(JuniorException):
    """Database related errors"""

    def __init__(self, message: str):
        super().__init__(message, code="DB_ERROR")

class AIAgentError(JuniorException):
    """AI Agent related errors"""

    def __init__(self, message: str, agent_name: Optional[str] = None):
        self.agent_name = agent_name
        super().__init__(message, code="AGENT_ERROR")

class RAGError(JuniorException):
    """RAG pipeline related errors"""

    def __init__(self, message: str):
        super().__init__(message, code="RAG_ERROR")

class CitationError(JuniorException):
    """Citation verification errors"""

    def __init__(self, message: str, citation: Optional[str] = None):
        self.citation = citation
        super().__init__(message, code="CITATION_ERROR")

class PrivacyError(JuniorException):
    """Privacy/PII related errors"""

    def __init__(self, message: str):
        super().__init__(message, code="PRIVACY_ERROR")

class DocumentError(JuniorException):
    """Document processing errors"""

    def __init__(self, message: str, document_id: Optional[str] = None):
        self.document_id = document_id
        super().__init__(message, code="DOC_ERROR")

class TranslationError(JuniorException):
    """Translation related errors"""

    def __init__(self, message: str, source_lang: Optional[str] = None, target_lang: Optional[str] = None):
        self.source_lang = source_lang
        self.target_lang = target_lang
        super().__init__(message, code="TRANSLATION_ERROR")

class ValidationError(JuniorException):
    """Validation errors"""

    def __init__(self, message: str, field: Optional[str] = None):
        self.field = field
        super().__init__(message, code="VALIDATION_ERROR")
