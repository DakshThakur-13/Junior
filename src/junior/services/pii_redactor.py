"""
PII Redactor Service using GLiNER
Implements DPDP Act compliant local redaction
"""

import re
from typing import Any, Optional
from dataclasses import dataclass

from junior.core import settings, get_logger
from junior.core.exceptions import PrivacyError

logger = get_logger(__name__)

@dataclass
class RedactionResult:
    """Result of PII redaction"""
    original_text: str
    redacted_text: str
    redactions: list[dict]
    entities_found: int

class PIIRedactor:
    """
    PII (Personally Identifiable Information) Redactor

    Uses GLiNER for zero-shot named entity recognition to identify
    and redact sensitive personal information before cloud processing.

    This ensures DPDP Act compliance by keeping PII local.
    """

    # Entity types to redact
    SENSITIVE_ENTITIES = [
        "person",
        "phone number",
        "email",
        "address",
        "aadhaar number",
        "pan number",
        "bank account",
        "passport number",
        "date of birth",
    ]

    # Redaction placeholders
    REDACTION_MAP = {
        "person": "[PERSON_NAME]",
        "phone number": "[PHONE]",
        "email": "[EMAIL]",
        "address": "[ADDRESS]",
        "aadhaar number": "[AADHAAR]",
        "pan number": "[PAN]",
        "bank account": "[BANK_ACCOUNT]",
        "passport number": "[PASSPORT]",
        "date of birth": "[DOB]",
    }

    def __init__(self, use_gliner: bool = True):
        self.use_gliner = use_gliner
        self._model: Optional[Any] = None
        self.enabled = settings.enable_pii_redaction

    @property
    def model(self) -> Optional[Any]:
        """Lazy-load GLiNER model"""
        if self._model is None and self.use_gliner:
            try:
                from gliner import GLiNER
                self._model = GLiNER.from_pretrained("urchade/gliner_base")
                logger.info("GLiNER model loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load GLiNER: {e}. Using regex fallback.")
                self.use_gliner = False
        return self._model

    def redact(self, text: str) -> RedactionResult:
        """
        Redact PII from text

        Args:
            text: Text to redact

        Returns:
            RedactionResult with redacted text and metadata
        """
        if not self.enabled:
            return RedactionResult(
                original_text=text,
                redacted_text=text,
                redactions=[],
                entities_found=0,
            )

        logger.debug(f"Redacting PII from text of length {len(text)}")

        redactions = []
        redacted_text = text

        # Try GLiNER first, fall back to regex
        if self.use_gliner and self.model:
            redactions = self._redact_with_gliner(text)
        else:
            redactions = self._redact_with_regex(text)

        # Apply redactions (from end to start to preserve positions)
        for redaction in sorted(redactions, key=lambda x: x["start"], reverse=True):
            redacted_text = (
                redacted_text[:redaction["start"]] +
                redaction["replacement"] +
                redacted_text[redaction["end"]:]
            )

        logger.info(f"Redacted {len(redactions)} PII entities")

        return RedactionResult(
            original_text=text,
            redacted_text=redacted_text,
            redactions=redactions,
            entities_found=len(redactions),
        )

    def _redact_with_gliner(self, text: str) -> list[dict]:
        """
        Redact using GLiNER NER model

        Args:
            text: Text to analyze

        Returns:
            List of redaction dictionaries
        """
        redactions = []

        model = self.model
        if model is None:
            return self._redact_with_regex(text)

        try:
            # Get entities from GLiNER
            entities = model.predict_entities(
                text,
                self.SENSITIVE_ENTITIES,
                threshold=0.5,
            )

            for entity in entities:
                entity_type = entity["label"].lower()
                replacement = self.REDACTION_MAP.get(entity_type, "[REDACTED]")

                redactions.append({
                    "start": entity["start"],
                    "end": entity["end"],
                    "original": entity["text"],
                    "type": entity_type,
                    "replacement": replacement,
                    "confidence": entity.get("score", 0.0),
                })

        except Exception as e:
            logger.error(f"GLiNER error: {e}")
            # Fall back to regex
            redactions = self._redact_with_regex(text)

        return redactions

    def _redact_with_regex(self, text: str) -> list[dict]:
        """
        Redact using regex patterns (fallback)

        Args:
            text: Text to analyze

        Returns:
            List of redaction dictionaries
        """
        redactions = []

        # Define regex patterns for common Indian PII
        patterns = {
            "phone number": r'\b(?:\+91[-\s]?)?[6-9]\d{9}\b',
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "aadhaar number": r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            "pan number": r'\b[A-Z]{5}\d{4}[A-Z]\b',
            "pin code": r'\b\d{6}\b',
        }

        for entity_type, pattern in patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Skip if this position is already redacted
                if any(r["start"] <= match.start() < r["end"] for r in redactions):
                    continue

                replacement = self.REDACTION_MAP.get(entity_type, "[REDACTED]")

                redactions.append({
                    "start": match.start(),
                    "end": match.end(),
                    "original": match.group(),
                    "type": entity_type,
                    "replacement": replacement,
                    "confidence": 0.9,  # High confidence for regex matches
                })

        return redactions

    def redact_document(self, document: dict) -> dict:
        """
        Redact PII from a document dictionary

        Args:
            document: Document with 'content' field

        Returns:
            Document with redacted content
        """
        if "content" not in document:
            return document

        result = self.redact(document["content"])

        return {
            **document,
            "content": result.redacted_text,
            "_pii_redacted": True,
            "_pii_count": result.entities_found,
        }

    def create_redaction_map(self, text: str) -> dict[str, str]:
        """
        Create a mapping of original values to redacted placeholders

        This can be used to restore original values after processing
        (with proper authorization)

        Args:
            text: Original text

        Returns:
            Dictionary mapping placeholders to original values
        """
        result = self.redact(text)

        # Create reverse mapping
        redaction_map = {}
        for i, redaction in enumerate(result.redactions):
            key = f"{redaction['replacement']}_{i}"
            redaction_map[key] = redaction["original"]

        return redaction_map
