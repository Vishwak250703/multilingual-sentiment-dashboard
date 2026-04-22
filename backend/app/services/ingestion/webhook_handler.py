"""
Webhook ingestion handler.
Validates and normalizes payloads from external systems before queuing.
"""
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def normalize_webhook_reviews(raw_reviews: list[dict]) -> list[dict]:
    """
    Normalize a list of webhook review payloads into a standard internal format.
    Handles various field names from different CRM/e-commerce systems.
    """
    normalized = []

    for item in raw_reviews:
        text = (
            item.get("text") or item.get("review") or item.get("body") or
            item.get("message") or item.get("content") or item.get("feedback") or ""
        )
        text = str(text).strip()
        if not text:
            continue

        # Parse date
        date_raw = item.get("date") or item.get("created_at") or item.get("timestamp")
        parsed_date: Optional[datetime] = None
        if date_raw:
            try:
                import pandas as pd
                dt = pd.to_datetime(date_raw, errors="coerce")
                if not pd.isna(dt):
                    parsed_date = dt.to_pydatetime()
            except Exception:
                pass

        normalized.append({
            "text": text,
            "date": parsed_date,
            "product_id": str(item.get("product_id", "") or "").strip() or None,
            "branch_id":  str(item.get("branch_id", "") or item.get("location_id", "") or "").strip() or None,
            "source":     str(item.get("source") or "webhook").strip(),
            "rating":     float(item["rating"]) if "rating" in item and item["rating"] is not None else None,
            "external_id": str(item.get("id") or item.get("external_id") or "").strip() or None,
        })

    return normalized
