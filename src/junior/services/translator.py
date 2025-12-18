"""
Translation Service for multilingual support
Implements the "Hinglish Bridge" feature with Legislative Glossary verification
"""

from typing import Any, Optional
from dataclasses import dataclass

from junior.core import settings, get_logger
from junior.core.types import Language
from junior.services.legal_glossary import get_glossary_service

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

    async def translate_response_intelligent(
        self,
        text: str,
        target_lang: Language,
        preserve_legal_terms: bool = True,
    ) -> TranslationResult:
        """
        Intelligent translation with Legislative Glossary verification.

        Process:
        1. Extract potential legal terms from text
        2. Verify each term against Legislative Department glossary
        3. AI checks if usage matches official definition
        4. Translate with verified terms preserved

        Args:
            text: English text to translate
            target_lang: Target language
            preserve_legal_terms: Whether to verify and preserve legal terms

        Returns:
            TranslationResult with verified term preservation
        """
        if target_lang == Language.ENGLISH:
            return TranslationResult(
                source_text=text,
                translated_text=text,
                source_language=Language.ENGLISH,
                target_language=target_lang,
                preserved_terms=[],
            )

        logger.info(f"[INTELLIGENT] Translating to {target_lang.value} with glossary verification...")

        # Step 1: Extract candidate legal terms
        candidate_terms = self._extract_legal_terms(text)

        # Step 2: Verify terms with glossary
        verified_terms = []
        if preserve_legal_terms and candidate_terms:
            glossary = get_glossary_service()

            for term in candidate_terms:
                try:
                    # Check if term exists in glossary
                    glossary_entry = await glossary.lookup_term(term)

                    if glossary_entry:
                        # Verify usage is correct
                        is_correct, explanation = await glossary.verify_term_meaning(term, text)

                        if is_correct:
                            logger.info(f"✓ Term '{term}' verified: {explanation[:50]}...")
                            verified_terms.append(term)
                        else:
                            logger.warning(f"✗ Term '{term}' usage questionable: {explanation[:50]}...")
                            # Still preserve it, but log the concern
                            verified_terms.append(term)
                    else:
                        # Not in glossary, but might still be legal term
                        if term in self.PRESERVE_TERMS:
                            verified_terms.append(term)

                except Exception as e:
                    logger.error(f"Failed to verify term '{term}': {e}")
                    # Fallback to preserving it anyway
                    if term in self.PRESERVE_TERMS:
                        verified_terms.append(term)
        else:
            verified_terms = self._find_preserved_terms(text) if preserve_legal_terms else []

        # Step 3: Translate with verified preservation
        translated = await self._translate_with_preservation(
            text, target_lang, verified_terms
        )

        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_language=Language.ENGLISH,
            target_language=target_lang,
            preserved_terms=verified_terms,
        )

    def _extract_legal_terms(self, text: str) -> list[str]:
        """
        Extract potential legal terms from text.
        Looks for capitalized phrases and known legal patterns.
        """
        import re

        candidates = []

        # Find terms from PRESERVE_TERMS that appear in text
        for term in self.PRESERVE_TERMS:
            if term.lower() in text.lower():
                candidates.append(term)

        # Find capitalized phrases (potential case names, act names)
        patterns = [
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\s+\(\d{4}\)',  # Case names with year
            r'\b(?:Article|Section|Order|Rule)\s+\d+[A-Z]?\b',  # Statutory references
            r'\b[A-Z][a-z]+\s+(?:Act|Code|Law|Procedure)\b',   # Act names
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            candidates.extend(matches)

        # Deduplicate
        return list(set(candidates))

    async def _translate_with_local_indictrans(
        self,
        text: str,
        source_lang: Language,
        target_lang: Language,
    ) -> Optional[str]:
        """
        Try to use locally-installed IndicTrans2 for translation.

        Returns None if IndicTrans2 is not installed or fails.
        Falls back to HF API or Groq LLM.
        """
        try:
            # Try importing IndicTrans2 local package
            from IndicTransToolkit import IndicProcessor

            # Determine direction
            if source_lang == Language.ENGLISH:
                direction = "en-indic"
            else:
                direction = "indic-en"

            # Initialize processor (cached after first call)
            cache_attr = f'_indictrans_{direction}'
            if not hasattr(self, cache_attr):
                logger.info(f"Initializing local IndicTrans2 ({direction})...")
                processor = IndicProcessor(direction=direction)
                setattr(self, cache_attr, processor)
            else:
                processor = getattr(self, cache_attr)

            # Get language codes
            src_code = self.INDICTRANS_CODES.get(source_lang.value, "eng_Latn")
            tgt_code = self.INDICTRANS_CODES.get(target_lang.value, "hin_Deva")

            # Translate
            result = processor.translate_paragraph(
                text,
                src_lang=src_code,
                tgt_lang=tgt_code,
            )

            logger.info("✓ Used local IndicTrans2")
            return result

        except ImportError:
            logger.debug("IndicTrans2 not installed locally, will use fallback")
            return None
        except Exception as e:
            logger.warning(f"Local IndicTrans2 failed: {e}")
            return None

    async def _translate_with_llm(
        self,
        text: str,
        source_lang: Language,
        target_lang: Language,
    ) -> str:
        """Translate using best available method: Local IndicTrans2 > HF API > Groq LLM."""

        # 1) Try local IndicTrans2 first (best quality, offline-capable)
        if settings.allow_hf_model_downloads:  # Only if user allows model downloads
            local_result = await self._translate_with_local_indictrans(text, source_lang, target_lang)
            if local_result:
                return local_result

        # 2) Try HF Inference API with IndicTrans2 (will likely fail with 410, but try anyway)
        if settings.huggingface_api_key:
            try:
                return await self._translate_with_indictrans(text, source_lang, target_lang)
            except Exception as e:
                logger.warning(f"HF IndicTrans2 failed: {e}. Falling back to LLM.")

        # 3) Fallback to Groq LLM if configured
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
        """
        Translate using AI4Bharat IndicTrans2.

        Note: The official IndicTrans2 models require custom code and cannot be used
        via HF Inference API (they return 410 Gone because inference=false).

        Instead, we use the HuggingFace pipeline API which requires the model to be
        loaded locally or use a community-hosted inference endpoint.

        For production, consider:
        1. Self-hosting IndicTrans2 with their official code
        2. Using a paid HF Inference Endpoint
        3. Using alternative translation models that support HF Inference API
        """
        import httpx

        # Determine model direction
        if source_lang == Language.ENGLISH:
            # English -> Indic
            model_id = "ai4bharat/indictrans2-en-indic-1B"
        else:
            # Indic -> English
            model_id = "ai4bharat/indictrans2-indic-en-1B"

        # Get FLORES-200 codes (IndicTrans2 uses these)
        src_code = self.INDICTRANS_CODES.get(source_lang.value, "eng_Latn")
        tgt_code = self.INDICTRANS_CODES.get(target_lang.value, "eng_Latn")

        # IndicTrans2 format: src_code + " tgt_code " + text
        # For example: "eng_Latn hin_Deva The court ruled in favor."
        prompt = f"{src_code} {tgt_code} {text}"

        # Try HuggingFace Inference API (will fail with 410 for IndicTrans2)
        url = f"https://api-inference.huggingface.co/models/{model_id}"
        headers = {
            "Authorization": f"Bearer {settings.huggingface_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": prompt,
            "options": {"wait_for_model": True},
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)

            # If model requires custom code (410 Gone), try alternative approach
            if response.status_code == 410:
                # Fall back to using a simpler translation model that supports inference
                logger.info(f"IndicTrans2 requires custom code. Trying alternative model...")

                # Use Facebook's NLLB-200 which supports Hindi and is available on HF Inference
                alt_model = "facebook/nllb-200-distilled-600M"
                alt_url = f"https://api-inference.huggingface.co/models/{alt_model}"

                # NLLB language codes
                nllb_codes = {
                    "en": "eng_Latn",
                    "hi": "hin_Deva",
                    "mr": "mar_Deva",
                    "ta": "tam_Taml",
                    "te": "tel_Telu",
                    "bn": "ben_Beng",
                    "gu": "guj_Gujr",
                    "kn": "kan_Knda",
                    "ml": "mal_Mlym",
                    "pa": "pan_Guru",
                }

                src_nllb = nllb_codes.get(source_lang.value, "eng_Latn")
                tgt_nllb = nllb_codes.get(target_lang.value, "hin_Deva")

                alt_payload = {
                    "inputs": text,
                    "parameters": {
                        "src_lang": src_nllb,
                        "tgt_lang": tgt_nllb,
                    },
                    "options": {"wait_for_model": True},
                }

                alt_response = await client.post(alt_url, headers=headers, json=alt_payload)
                alt_response.raise_for_status()
                result = alt_response.json()

                # Parse NLLB response
                if isinstance(result, list) and len(result) > 0:
                    if isinstance(result[0], dict):
                        return result[0].get("translation_text", str(result[0]))
                    return str(result[0])
                elif isinstance(result, dict):
                    return result.get("translation_text", str(result))
                return str(result)

            response.raise_for_status()
            result = response.json()

            # Parse IndicTrans2 response (if it ever works)
            if isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], dict):
                    return result[0].get("generated_text", result[0].get("translation_text", str(result[0])))
                return str(result[0])
            elif isinstance(result, dict):
                return result.get("generated_text", result.get("translation_text", str(result)))
            elif isinstance(result, str):
                return result

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
