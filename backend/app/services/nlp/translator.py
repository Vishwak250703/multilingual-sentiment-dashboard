"""
Translation service using deep-translator (no API key required).
Translates any supported language → English.
"""
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Simple in-process cache: (text, lang) → translated
_cache: dict[tuple[str, str], str] = {}
_MAX_CACHE = 2000


def translate_to_english(text: str, source_language: str) -> str:
    """
    Translate text from source_language to English.
    Returns original text if translation fails or is unnecessary.
    """
    if source_language == "en":
        return text

    cache_key = (text[:200], source_language)
    if cache_key in _cache:
        return _cache[cache_key]

    try:
        from deep_translator import GoogleTranslator

        # deep-translator uses 'zh-CN' format
        src = _normalize_lang_code(source_language)

        translated = GoogleTranslator(source=src, target="en").translate(text)
        if not translated:
            return text

        # Cache management
        if len(_cache) >= _MAX_CACHE:
            # Drop oldest 200 entries
            for k in list(_cache.keys())[:200]:
                del _cache[k]

        _cache[cache_key] = translated
        return translated

    except Exception as e:
        logger.warning(f"Translation failed ({source_language} → en): {e}")
        return text  # Graceful fallback — process original text


def _normalize_lang_code(code: str) -> str:
    """Normalize language codes for deep-translator."""
    mapping = {
        "zh-cn": "zh-CN",
        "zh-tw": "zh-TW",
        "hi": "hi",
        "te": "te",
        "ta": "ta",
        "kn": "kn",
        "mr": "mr",
        "bn": "bn",
        "gu": "gu",
        "ur": "ur",
    }
    return mapping.get(code, code)
