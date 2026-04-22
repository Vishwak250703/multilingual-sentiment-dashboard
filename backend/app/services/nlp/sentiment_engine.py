"""
Sentiment analysis engine powered by Claude.
Handles both document-level and sentence-level sentiment with confidence scores.
"""
import json
import logging
import re
from typing import Optional
from anthropic import Anthropic
from app.core.config import settings

logger = logging.getLogger(__name__)
_client: Optional[Anthropic] = None


def get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


SENTIMENT_PROMPT = """You are an expert sentiment analysis AI. Analyze the following customer review text.

Return ONLY valid JSON (no markdown, no explanation) in this exact format:
{{
  "sentiment": "positive" | "negative" | "neutral",
  "sentiment_score": <float between -1.0 (very negative) and 1.0 (very positive)>,
  "confidence": <float between 0.0 and 1.0>,
  "sentence_sentiments": [
    {{
      "sentence": "<sentence text>",
      "sentiment": "positive" | "negative" | "neutral",
      "score": <float -1.0 to 1.0>
    }}
  ],
  "keywords": ["<key phrase 1>", "<key phrase 2>"]
}}

Rules:
- sentiment_score: 0.6 to 1.0 = positive, -0.6 to -1.0 = negative, -0.5 to 0.5 = neutral
- Split into meaningful sentences (not too granular)
- keywords: extract 2-5 most impactful phrases (positive or negative)
- confidence: how certain you are about the overall sentiment

Review text:
{text}"""


def analyze_sentiment(text: str) -> dict:
    """
    Analyze sentiment of a text using Claude.
    Returns structured sentiment data with document and sentence-level results.
    """
    if not text or len(text.strip()) < 3:
        return _empty_result()

    try:
        client = get_client()
        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": SENTIMENT_PROMPT.format(text=text[:2000]),
                }
            ],
        )

        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        result = json.loads(raw)

        # Validate and clamp values
        result["sentiment_score"] = max(-1.0, min(1.0, float(result.get("sentiment_score", 0.0))))
        result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.8))))
        result["sentiment"] = result.get("sentiment", "neutral")
        result["sentence_sentiments"] = result.get("sentence_sentiments", [])
        result["keywords"] = result.get("keywords", [])

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude sentiment response: {e}\nRaw: {raw[:300]}")
        return _fallback_result(text)
    except Exception as e:
        logger.error(f"Sentiment analysis error: {e}")
        return _empty_result()


def _empty_result() -> dict:
    return {
        "sentiment": "neutral",
        "sentiment_score": 0.0,
        "confidence": 0.0,
        "sentence_sentiments": [],
        "keywords": [],
    }


def _fallback_result(text: str) -> dict:
    """Simple keyword-based fallback if Claude fails."""
    text_lower = text.lower()
    positive_words = ["good", "great", "excellent", "amazing", "love", "perfect", "best", "happy"]
    negative_words = ["bad", "terrible", "awful", "horrible", "hate", "worst", "poor", "disappointed"]

    pos = sum(1 for w in positive_words if w in text_lower)
    neg = sum(1 for w in negative_words if w in text_lower)

    if pos > neg:
        return {"sentiment": "positive", "sentiment_score": 0.5, "confidence": 0.4, "sentence_sentiments": [], "keywords": []}
    elif neg > pos:
        return {"sentiment": "negative", "sentiment_score": -0.5, "confidence": 0.4, "sentence_sentiments": [], "keywords": []}
    return _empty_result()
