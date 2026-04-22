"""
Unified NLP processing pipeline.
Every review — regardless of source (CSV, API, webhook) — runs through this.

Steps:
1. Clean text
2. PII mask
3. Detect language
4. Translate → English (if needed)
5. Sentiment analysis (doc + sentence level)
6. ABSA (aspect-based sentiment)
7. Keyword extraction (from sentiment result)
8. Return enriched record
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """Basic text cleaning — strip excess whitespace, remove null bytes."""
    if not text:
        return ""
    text = text.replace("\x00", "").strip()
    # Collapse multiple newlines/spaces
    import re
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {3,}', ' ', text)
    return text


def process_review(
    raw_text: str,
    tenant_id: str,
    source: str = "csv",
    product_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    external_id: Optional[str] = None,
    review_date: Optional[datetime] = None,
) -> dict:
    """
    Run a single review through the full NLP pipeline.
    Returns a dict ready to be stored as a Review model.
    """
    from app.services.nlp.language_detector import detect_language, needs_translation
    from app.services.nlp.translator import translate_to_english
    from app.services.nlp.sentiment_engine import analyze_sentiment
    from app.services.nlp.absa_engine import analyze_aspects
    from app.services.security.pii_masker import mask_pii

    # Step 1: Clean
    text = clean_text(raw_text)
    if not text:
        return _failed_record(raw_text, tenant_id, source, "Empty text after cleaning")

    # Step 2: PII mask
    masked_text, was_masked = mask_pii(text)

    # Step 3: Language detection
    detected_lang, lang_confidence = detect_language(masked_text)

    # Step 4: Translation
    translated_text = None
    processing_text = masked_text  # text used for NLP

    if needs_translation(detected_lang):
        translated = translate_to_english(masked_text, detected_lang)
        if translated and translated != masked_text:
            translated_text = translated
            processing_text = translated_text

    # Step 5: Sentiment analysis
    sentiment_result = analyze_sentiment(processing_text)

    # Step 6: ABSA
    aspects = analyze_aspects(processing_text)

    # Step 7: Assemble record
    return {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "raw_text": raw_text,
        "translated_text": translated_text,
        "original_language": detected_lang,
        "detected_language": detected_lang,
        "source": source,
        "product_id": product_id,
        "branch_id": branch_id,
        "external_id": external_id,
        "sentiment": sentiment_result.get("sentiment", "neutral"),
        "sentiment_score": sentiment_result.get("sentiment_score", 0.0),
        "confidence": sentiment_result.get("confidence", 0.0),
        "sentence_sentiments": sentiment_result.get("sentence_sentiments", []),
        "aspects": aspects,
        "keywords": sentiment_result.get("keywords", []),
        "is_pii_masked": was_masked,
        "processing_status": "completed",
        "review_date": review_date,
        "created_at": datetime.now(timezone.utc),
        "processed_at": datetime.now(timezone.utc),
    }


def _failed_record(raw_text: str, tenant_id: str, source: str, reason: str) -> dict:
    logger.warning(f"Review processing failed: {reason}")
    return {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "raw_text": raw_text,
        "translated_text": None,
        "original_language": "en",
        "detected_language": None,
        "source": source,
        "product_id": None,
        "branch_id": None,
        "external_id": None,
        "sentiment": None,
        "sentiment_score": None,
        "confidence": None,
        "sentence_sentiments": None,
        "aspects": None,
        "keywords": None,
        "is_pii_masked": False,
        "processing_status": "failed",
        "review_date": None,
        "created_at": datetime.now(timezone.utc),
        "processed_at": datetime.now(timezone.utc),
    }
