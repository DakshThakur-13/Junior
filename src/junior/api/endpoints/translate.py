"""
Translation endpoints
"""

from fastapi import APIRouter, HTTPException

from junior.core import get_logger
from junior.core.types import Language
from junior.services import TranslationService
from junior.api.schemas import TranslateRequest, TranslateResponse

router = APIRouter()
logger = get_logger(__name__)

@router.post("/", response_model=TranslateResponse)
async def translate(request: TranslateRequest):
    """
    Translate text between languages

    Implements the "Hinglish Bridge" feature:
    - Preserves legal terminology in English
    - Translates remaining content to target language
    """
    logger.info(f"Translation request to {request.target_language.value}")

    try:
        translator = TranslationService()

        # Detect source language if needed
        source_lang = translator.detect_language(request.text)

        if source_lang == request.target_language:
            # No translation needed
            return TranslateResponse(
                original_text=request.text,
                translated_text=request.text,
                source_language=source_lang.value,
                target_language=request.target_language.value,
                preserved_terms=[],
            )

        # Translate
        result = await translator.translate_response(
            request.text,
            request.target_language,
            preserve_legal_terms=request.preserve_legal_terms,
        )

        return TranslateResponse(
            original_text=result.source_text,
            translated_text=result.translated_text,
            source_language=result.source_language.value,
            target_language=result.target_language.value,
            preserved_terms=result.preserved_terms,
        )

    except Exception as e:
        logger.error(f"Translation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/aligned")
async def translate_aligned(request: TranslateRequest):
    """
    Translate text with sentence alignment for "Hover-to-Reveal" UI.
    Returns list of {original, translated} pairs.
    """
    try:
        translator = TranslationService()
        results = await translator.translate_aligned(
            request.text,
            request.target_language
        )
        return {"aligned_segments": results}
    except Exception as e:
        logger.error(f"Aligned translation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query")
async def translate_query(query: str, source_lang: str = "auto"):
    """
    Translate a search query to English

    Used when users input queries in vernacular languages.
    The translated query is used to search the English case law database.
    """
    logger.info(f"Query translation: {query[:50]}...")

    try:
        translator = TranslationService()

        # Auto-detect if needed
        if source_lang == "auto":
            detected = translator.detect_language(query)
        else:
            detected = Language(source_lang)

        # Translate to English
        result = await translator.translate_query(
            query,
            source_lang=detected,
            target_lang=Language.ENGLISH,
        )

        return {
            "original_query": query,
            "translated_query": result.translated_text,
            "detected_language": detected.value,
        }

    except Exception as e:
        logger.error(f"Query translation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/languages")
async def list_languages():
    """
    List supported languages for translation
    """
    translator = TranslationService()

    return {
        "languages": [
            {"code": code, "name": name}
            for code, name in translator.LANGUAGE_NAMES.items()
        ],
        "default": "en",
    }
