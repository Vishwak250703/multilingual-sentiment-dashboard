"""
Aspect-Based Sentiment Analysis (ABSA) engine.
Extracts sentiment for specific business-relevant aspects using Claude.
"""
import json
import logging
import re
from typing import Optional
from anthropic import Anthropic
from app.core.config import settings

logger = logging.getLogger(__name__)

# Predefined aspect categories per domain
ASPECT_CATEGORIES = [
    "price", "value", "delivery", "shipping", "service", "support",
    "quality", "cleanliness", "food", "ambiance", "location",
    "ui", "app", "website", "staff", "packaging", "speed", "accuracy",
]

ABSA_PROMPT = """You are an expert in Aspect-Based Sentiment Analysis. Analyze this customer review and identify aspects that are explicitly or implicitly mentioned.

Only include aspects that are actually referenced in the review (directly or by implication). Do not invent aspects.

Return ONLY valid JSON (no markdown, no explanation):
{{
  "aspects": {{
    "<aspect_name>": {{
      "sentiment": "positive" | "negative" | "neutral",
      "score": <float -1.0 to 1.0>,
      "evidence": "<exact phrase from review that supports this>"
    }}
  }}
}}

Relevant aspect categories to consider: {aspects}

If none of these aspects are mentioned, return: {{"aspects": {{}}}}

Review:
{text}"""


def analyze_aspects(text: str) -> dict[str, str]:
    """
    Perform aspect-based sentiment analysis.
    Returns dict: {aspect: sentiment_label}
    e.g. {"delivery": "negative", "price": "positive", "quality": "neutral"}
    """
    if not text or len(text.strip()) < 10:
        return {}

    try:
        from app.services.nlp.sentiment_engine import get_client
        client = get_client()

        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": ABSA_PROMPT.format(
                        text=text[:1500],
                        aspects=", ".join(ASPECT_CATEGORIES),
                    ),
                }
            ],
        )

        raw = response.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        parsed = json.loads(raw)
        aspects_raw = parsed.get("aspects", {})

        # Flatten to simple {aspect: sentiment} for storage
        result: dict[str, str] = {}
        for aspect, data in aspects_raw.items():
            if isinstance(data, dict):
                result[aspect.lower()] = data.get("sentiment", "neutral")
            elif isinstance(data, str):
                result[aspect.lower()] = data

        return result

    except json.JSONDecodeError as e:
        logger.error(f"ABSA JSON parse error: {e}")
        return {}
    except Exception as e:
        logger.error(f"ABSA error: {e}")
        return {}
