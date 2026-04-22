"""
Language detection service.
Uses langdetect as primary, langid as fallback for robustness.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Language code → human-readable name
LANGUAGE_NAMES: dict[str, str] = {
    "en": "English", "hi": "Hindi", "te": "Telugu", "ta": "Tamil",
    "kn": "Kannada", "mr": "Marathi", "bn": "Bengali", "gu": "Gujarati",
    "ur": "Urdu", "ar": "Arabic", "fr": "French", "de": "German",
    "es": "Spanish", "pt": "Portuguese", "ja": "Japanese", "zh-cn": "Chinese",
    "zh-tw": "Chinese (Traditional)", "ko": "Korean", "it": "Italian",
    "ru": "Russian", "tr": "Turkish", "vi": "Vietnamese", "id": "Indonesian",
    "ms": "Malay", "th": "Thai",
}

# Languages we can translate to English
TRANSLATABLE_LANGUAGES = {
    "hi", "te", "ta", "kn", "mr", "bn", "gu", "ur", "ar",
    "fr", "de", "es", "pt", "ja", "zh-cn", "zh-tw", "ko",
    "it", "ru", "tr", "vi", "id", "ms", "th",
}


def detect_language(text: str) -> tuple[str, float]:
    """
    Detect language of text.
    Returns (language_code, confidence).
    Falls back to 'en' if detection fails.
    """
    if not text or len(text.strip()) < 3:
        return "en", 1.0

    # Primary: langdetect
    try:
        from langdetect import detect_langs
        results = detect_langs(text)
        if results:
            top = results[0]
            lang = top.lang
            # Normalize Chinese variants
            if lang in ("zh-cn", "zh-tw", "zh"):
                lang = "zh-cn"
            return lang, round(top.prob, 3)
    except Exception as e:
        logger.debug(f"langdetect failed: {e}")

    # Fallback: langid
    try:
        import langid
        lang, confidence = langid.classify(text)
        return lang, round(abs(confidence), 3)
    except Exception as e:
        logger.debug(f"langid failed: {e}")

    return "en", 0.5


def needs_translation(language_code: str) -> bool:
    """Returns True if the text needs to be translated to English."""
    return language_code in TRANSLATABLE_LANGUAGES


def get_language_name(code: str) -> str:
    return LANGUAGE_NAMES.get(code, code.upper())
