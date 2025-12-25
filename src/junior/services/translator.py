"""
Translation Service for multilingual support
Implements the "Hinglish Bridge" feature
"""

from typing import Any, Optional
from dataclasses import dataclass

from junior.core import settings, get_logger
from junior.core.types import Language

logger = get_logger(__name__)


@dataclass
class TranslationResult:
    """Result of translation"""
    source_text: str
    translated_text: str
    source_language: Language
    target_language: Language
    preserved_terms: list[str]


class TranslationService:
    """
    Translation Service for Indian languages
    
    Implements Cross-Lingual Information Retrieval (CLIR) that:
    - Accepts queries in vernacular languages
    - Searches English repositories
    - Returns results with key legal terms preserved in English
    
    This is the "Hinglish Bridge" feature from the Junior spec.
    """
    
    # Legal terms that should ALWAYS remain in English
    PRESERVE_TERMS = [
        # Latin maxims
        "res judicata", "stare decisis", "prima facie", "inter alia",
        "suo motu", "locus standi", "ultra vires", "mala fide", "bona fide",
        "habeas corpus", "mandamus", "certiorari", "quo warranto",
        
        # Legal terminology
        "Interim Relief", "Stay Order", "Bail", "Anticipatory Bail",
        "Writ Petition", "Special Leave Petition", "Civil Appeal",
        "Criminal Appeal", "Review Petition", "Curative Petition",
        "Ratio Decidendi", "Obiter Dicta", "Per Incuriam",
        "Doctrine of Precedent", "Judicial Review",
        
        # Procedural terms
        "Section", "Article", "Order", "Rule", "Clause",
        "Plaintiff", "Defendant", "Petitioner", "Respondent",
        "Appellant", "Appellee", "Complainant", "Accused",
        
        # Acts and Laws
        "Indian Penal Code", "IPC", "CrPC", "CPC",
        "Indian Evidence Act", "Constitution of India",
        "DPDP Act", "IT Act", "Arbitration Act",
    ]
    
    # Language code to name mapping
    LANGUAGE_NAMES = {
        "hi": "Hindi",
        "hi-latn": "Hinglish",  # Hindi in Roman script
        "mr": "Marathi",
        "ta": "Tamil",
        "te": "Telugu",
        "bn": "Bengali",
        "gu": "Gujarati",
        "kn": "Kannada",
        "ml": "Malayalam",
        "pa": "Punjabi",
        "en": "English",
    }

    # IndicTrans2 Language Codes (FLORES-200 format)
    INDICTRANS_CODES = {
        "en": "eng_Latn",
        "hi": "hin_Deva",
        "hi-latn": "hin_Latn",  # Hindi in Roman script (Hinglish)
        "mr": "mar_Deva",
        "ta": "tam_Taml",
        "te": "tel_Telu",
        "bn": "ben_Beng",
        "gu": "guj_Gujr",
        "kn": "kan_Knda",
        "ml": "mal_Mlym",
        "pa": "pan_Guru",
    }
    
    def __init__(self):
        self._translator = None
    
    def detect_language(self, text: str) -> Language:
        """
        Detect the language of input text
        
        Args:
            text: Input text
            
        Returns:
            Detected Language enum
        """
        # Simple detection based on character ranges
        # In production, use a proper language detection library
        
        # Check for Devanagari (Hindi, Marathi)
        if any('\u0900' <= c <= '\u097F' for c in text):
            # Could be Hindi or Marathi - default to Hindi
            return Language.HINDI
        
        # Check for Tamil
        if any('\u0B80' <= c <= '\u0BFF' for c in text):
            return Language.TAMIL
        
        # Check for Telugu
        if any('\u0C00' <= c <= '\u0C7F' for c in text):
            return Language.TELUGU
        
        # Check for Bengali
        if any('\u0980' <= c <= '\u09FF' for c in text):
            return Language.BENGALI
        
        # Check for Gujarati
        if any('\u0A80' <= c <= '\u0AFF' for c in text):
            return Language.GUJARATI
        
        # Check for Kannada
        if any('\u0C80' <= c <= '\u0CFF' for c in text):
            return Language.KANNADA
        
        # Check for Malayalam
        if any('\u0D00' <= c <= '\u0D7F' for c in text):
            return Language.MALAYALAM
        
        # Check for Gurmukhi (Punjabi)
        if any('\u0A00' <= c <= '\u0A7F' for c in text):
            return Language.PUNJABI
        
        # Default to English
        return Language.ENGLISH
    
    async def translate_query(
        self,
        query: str,
        source_lang: Optional[Language] = None,
        target_lang: Language = Language.ENGLISH,
    ) -> TranslationResult:
        """
        Translate a search query to English for searching
        
        Args:
            query: Query text (possibly in vernacular)
            source_lang: Source language (auto-detected if None)
            target_lang: Target language (default English)
            
        Returns:
            TranslationResult with translated query
        """
        # Detect source language if not provided
        if source_lang is None:
            source_lang = self.detect_language(query)
        
        # If already in target language, return as-is
        if source_lang == target_lang:
            return TranslationResult(
                source_text=query,
                translated_text=query,
                source_language=source_lang,
                target_language=target_lang,
                preserved_terms=[],
            )
        
        logger.info(f"Translating from {source_lang.value} to {target_lang.value}")
        
        # Translate using LLM (in production, use IndicTrans2)
        translated = await self._translate_with_llm(
            query, source_lang, target_lang
        )
        
        return TranslationResult(
            source_text=query,
            translated_text=translated,
            source_language=source_lang,
            target_language=target_lang,
            preserved_terms=self._find_preserved_terms(translated),
        )
    
    async def translate_aligned(
        self,
        text: str,
        target_lang: Language,
    ) -> list[dict[str, str]]:
        """
        Translate text while maintaining sentence alignment.
        Returns a list of { "original": "...", "translated": "..." } pairs.
        Used for the "Bilingual Toggle" / "Hover-to-Reveal" feature.
        """
        import re
        
        # Simple sentence splitting (can be improved with NLTK/Spacy)
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        
        aligned_results = []
        
        # Translate each sentence (or batch them in production)
        # For now, we loop. In prod, use batch API.
        for sentence in sentences:
            try:
                translated = await self.translate_response(
                    text=sentence,
                    target_lang=target_lang,
                    preserve_legal_terms=True
                )
                aligned_results.append({
                    "original": sentence,
                    "translated": translated.translated_text
                })
            except Exception as e:
                logger.error(f"Failed to translate sentence: {sentence[:20]}... Error: {e}")
                aligned_results.append({
                    "original": sentence,
                    "translated": sentence # Fallback
                })
                
        return aligned_results

    async def translate_response(
        self,
        text: str,
        target_lang: Language,
        preserve_legal_terms: bool = True,
    ) -> TranslationResult:
        """
        Translate a response while preserving legal terminology
        
        This implements the "Hinglish Bridge" - translating content
        while keeping key legal terms in English.
        
        Args:
            text: English text to translate
            target_lang: Target language
            preserve_legal_terms: Whether to keep legal terms in English
            
        Returns:
            TranslationResult
        """
        if target_lang == Language.ENGLISH:
            return TranslationResult(
                source_text=text,
                translated_text=text,
                source_language=Language.ENGLISH,
                target_language=target_lang,
                preserved_terms=[],
            )
        
        logger.info(f"Translating response to {target_lang.value}")
        
        # Find terms to preserve
        preserved = []
        if preserve_legal_terms:
            preserved = self._find_preserved_terms(text)
        
        # Translate with preservation
        translated = await self._translate_with_preservation(
            text, target_lang, preserved
        )
        
        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_language=Language.ENGLISH,
            target_language=target_lang,
            preserved_terms=preserved,
        )
    
    def _find_preserved_terms(self, text: str) -> list[str]:
        """Find legal terms in text that should be preserved"""
        found: list[str] = []
        text_lower = (text or "").lower()
        for term in self.PRESERVE_TERMS:
            if term.lower() in text_lower:
                found.append(term)
        return found

    async def _translate_with_llm(
        self,
        text: str,
        source_lang: Language,
        target_lang: Language,
    ) -> str:
        """Translate using AI4Bharat IndicTrans2 (HF) with Groq fallback."""
        # 1) Prefer IndicTrans2 for Indian language translation
        if settings.huggingface_api_key:
            try:
                return await self._translate_with_indictrans(text, source_lang, target_lang)
            except Exception as e:
                logger.warning(f"IndicTrans2 translation failed: {e}. Falling back to LLM.")

        # 2) Fallback to Groq LLM if configured
        if settings.groq_api_key:
            from langchain_groq import ChatGroq
            from langchain_core.messages import HumanMessage, SystemMessage
            from pydantic import SecretStr

            source_name = self.LANGUAGE_NAMES.get(source_lang.value, source_lang.value)
            target_name = self.LANGUAGE_NAMES.get(target_lang.value, target_lang.value)

            llm = ChatGroq(
                model=settings.default_llm_model,
                api_key=SecretStr(settings.groq_api_key),
                temperature=0.1,
            )

            messages = [
                SystemMessage(
                    content=(
                        "You are a legal translator specializing in Indian law.\n"
                        f"Translate the following text from {source_name} to {target_name}.\n"
                        "Preserve all legal terminology, case names, and statutory references in their original form.\n"
                        "Maintain the formal legal register appropriate for court documents."
                    )
                ),
                HumanMessage(content=text),
            ]

            response = await llm.ainvoke(messages)
            content: Any = response.content
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "".join(part if isinstance(part, str) else str(part) for part in content)
            return str(content)

        # 3) No translation backend available
        return text

    async def _translate_with_indictrans(
        self,
        text: str,
        source_lang: Language,
        target_lang: Language,
    ) -> str:
        """Translate using AI4Bharat IndicTrans2 via Hugging Face."""
        from langchain_huggingface import HuggingFaceEndpoint
        
        # Determine model direction
        if source_lang == Language.ENGLISH:
            # English -> Indic
            repo_id = "ai4bharat/indictrans2-en-indic-1B"
        else:
            # Indic -> English (or Indic -> Indic, but we mostly do Indic <-> En)
            repo_id = "ai4bharat/indictrans2-indic-en-1B"
            
        # Get FLORES-200 codes
        src_code = self.INDICTRANS_CODES.get(source_lang.value, "eng_Latn")
        tgt_code = self.INDICTRANS_CODES.get(target_lang.value, "eng_Latn")
        
        def _make_endpoint(**kwargs):
            try:
                return HuggingFaceEndpoint(**kwargs)
            except TypeError:
                if "repo_id" in kwargs and "model" not in kwargs:
                    alt_kwargs = dict(kwargs)
                    alt_kwargs["model"] = alt_kwargs.pop("repo_id")
                    return HuggingFaceEndpoint(**alt_kwargs)
                raise

        llm = _make_endpoint(
            repo_id=repo_id,
            task="text2text-generation",
            huggingfacehub_api_token=settings.huggingface_api_key,
            model_kwargs={
                "src_lang": src_code,
                "tgt_lang": tgt_code,
            },
        )

        result = await llm.ainvoke(text)
        if isinstance(result, str):
            return result
        if hasattr(result, "content"):
            return str(getattr(result, "content"))
        return str(result)
    
    async def _translate_with_preservation(
        self,
        text: str,
        target_lang: Language,
        preserve_terms: list[str],
    ) -> str:
        """
        Translate while explicitly preserving specific terms
        """
        import re

        # 1) Prefer IndicTrans2 if available; preserve terms via placeholder tokens.
        if settings.huggingface_api_key:
            try:
                token_map: dict[str, str] = {}
                protected_text = text

                for i, term in enumerate(preserve_terms or []):
                    token = f"__JUNIOR_TERM_{i}__"
                    token_map[token] = term
                    # Replace case-insensitively, but re-insert the canonical English term.
                    protected_text = re.sub(
                        re.escape(term),
                        token,
                        protected_text,
                        flags=re.IGNORECASE,
                    )

                translated = await self._translate_with_indictrans(
                    protected_text,
                    source_lang=Language.ENGLISH,
                    target_lang=target_lang,
                )

                # Restore preserved terms exactly
                for token, term in token_map.items():
                    translated = translated.replace(token, term)

                return translated
            except Exception as e:
                logger.warning(f"IndicTrans2 preserved-term translation failed: {e}. Falling back to LLM.")

        # 2) Fallback to Groq LLM with explicit preserve list
        from langchain_groq import ChatGroq
        from langchain_core.messages import SystemMessage, HumanMessage
        from pydantic import SecretStr

        target_name = self.LANGUAGE_NAMES.get(target_lang.value, target_lang.value)

        preserve_list = "\n".join(f"- {term}" for term in (preserve_terms or []))

        api_key = SecretStr(settings.groq_api_key) if settings.groq_api_key else None

        llm = ChatGroq(
            model=settings.default_llm_model,
            api_key=api_key,
            temperature=0.1,
        )

        messages = [
            SystemMessage(
                content=(
                    "You are a legal translator specializing in Indian law.\n"
                    f"Translate the following text from English to {target_name}.\n\n"
                    "IMPORTANT: Keep these terms in English (do not translate them):\n"
                    f"{preserve_list}\n\n"
                    "These are legal terms that must remain in English for legal accuracy.\n"
                    f"Translate all other content to {target_name} while maintaining formal legal register."
                )
            ),
            HumanMessage(content=text),
        ]

        response = await llm.ainvoke(messages)
        content: Any = response.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(part if isinstance(part, str) else str(part) for part in content)
        return str(content)
