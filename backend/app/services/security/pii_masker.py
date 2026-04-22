"""
PII masking service using Microsoft Presidio.
Detects and anonymizes: names, emails, phone numbers, credit cards, IPs, etc.
Falls back to regex-based masking if Presidio is unavailable.
"""
import re
import logging

logger = logging.getLogger(__name__)

_analyzer = None
_anonymizer = None


def _get_presidio():
    """Lazy-load Presidio engines."""
    global _analyzer, _anonymizer
    if _analyzer is None:
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_anonymizer import AnonymizerEngine
            _analyzer = AnalyzerEngine()
            _anonymizer = AnonymizerEngine()
            logger.info("Presidio PII engine loaded.")
        except Exception as e:
            logger.warning(f"Presidio unavailable, using regex fallback: {e}")
    return _analyzer, _anonymizer


def mask_pii(text: str) -> tuple[str, bool]:
    """
    Mask PII in text.
    Returns (masked_text, was_masked: bool).
    """
    if not text:
        return text, False

    analyzer, anonymizer = _get_presidio()

    if analyzer and anonymizer:
        return _mask_with_presidio(text, analyzer, anonymizer)
    else:
        return _mask_with_regex(text)


def _mask_with_presidio(text: str, analyzer, anonymizer) -> tuple[str, bool]:
    try:
        results = analyzer.analyze(text=text, language="en")
        if not results:
            return text, False

        from presidio_anonymizer.entities import OperatorConfig
        anonymized = anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators={
                "PERSON":       OperatorConfig("replace", {"new_value": "[NAME]"}),
                "EMAIL_ADDRESS":OperatorConfig("replace", {"new_value": "[EMAIL]"}),
                "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[PHONE]"}),
                "CREDIT_CARD":  OperatorConfig("replace", {"new_value": "[CARD]"}),
                "IP_ADDRESS":   OperatorConfig("replace", {"new_value": "[IP]"}),
                "LOCATION":     OperatorConfig("replace", {"new_value": "[LOCATION]"}),
                "DATE_TIME":    OperatorConfig("keep", {}),  # Keep dates — useful for trend analysis
            },
        )
        return anonymized.text, True
    except Exception as e:
        logger.warning(f"Presidio masking failed: {e}")
        return _mask_with_regex(text)


def _mask_with_regex(text: str) -> tuple[str, bool]:
    """Regex-based PII masking as fallback."""
    original = text
    masked = False

    # Email
    new = re.sub(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    if new != text:
        text, masked = new, True

    # Phone (various formats)
    new = re.sub(r'\b(\+?\d[\d\s\-().]{7,}\d)\b', '[PHONE]', text)
    if new != text:
        text, masked = new, True

    # Credit card (16 digits grouped)
    new = re.sub(r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b', '[CARD]', text)
    if new != text:
        text, masked = new, True

    # IP address
    new = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]', text)
    if new != text:
        text, masked = new, True

    return text, masked
