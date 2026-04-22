"""
CSV/Excel file parser.
Auto-detects column names for text, date, product, branch, source.
Handles messy real-world files gracefully.
"""
import logging
import io
from typing import Optional
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)

# Column name aliases — matches common export formats from Shopify, Zendesk, etc.
TEXT_COLUMNS = [
    "review", "text", "comment", "feedback", "message", "body",
    "review_text", "review_body", "content", "description", "note",
    "customer_review", "ticket_body", "review text", "comment text",
]

DATE_COLUMNS = [
    "date", "created_at", "timestamp", "review_date", "submitted_at",
    "created", "date_created", "review date", "submission_date",
]

PRODUCT_COLUMNS = [
    "product", "product_id", "product_name", "item", "item_name",
    "sku", "product id", "product name",
]

BRANCH_COLUMNS = [
    "branch", "branch_id", "location", "store", "store_id",
    "outlet", "branch name", "location_id",
]

SOURCE_COLUMNS = [
    "source", "platform", "channel", "origin",
]

RATING_COLUMNS = [
    "rating", "score", "stars", "rate",
]


def _find_column(df: pd.DataFrame, aliases: list[str]) -> Optional[str]:
    """Find the first matching column (case-insensitive)."""
    lower_cols = {c.lower(): c for c in df.columns}
    for alias in aliases:
        if alias.lower() in lower_cols:
            return lower_cols[alias.lower()]
    return None


def parse_file(file_bytes: bytes, filename: str) -> tuple[list[dict], list[str]]:
    """
    Parse a CSV or Excel file.

    Returns:
        (records, errors) where records is a list of dicts with standardized keys:
        {text, date, product_id, branch_id, source, rating}
        errors is a list of row-level error messages.
    """
    errors: list[str] = []

    # Read file
    try:
        if filename.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
        else:
            # Try multiple encodings
            for encoding in ("utf-8", "latin-1", "cp1252"):
                try:
                    df = pd.read_csv(io.BytesIO(file_bytes), encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                return [], ["Could not decode file — please save as UTF-8"]
    except Exception as e:
        return [], [f"Failed to read file: {e}"]

    if df.empty:
        return [], ["File is empty"]

    # Strip whitespace from column names
    df.columns = df.columns.str.strip()

    # Detect columns
    text_col    = _find_column(df, TEXT_COLUMNS)
    date_col    = _find_column(df, DATE_COLUMNS)
    product_col = _find_column(df, PRODUCT_COLUMNS)
    branch_col  = _find_column(df, BRANCH_COLUMNS)
    source_col  = _find_column(df, SOURCE_COLUMNS)
    rating_col  = _find_column(df, RATING_COLUMNS)

    if not text_col:
        # Last resort: use the longest string column
        str_cols = df.select_dtypes(include="object").columns.tolist()
        if str_cols:
            text_col = max(str_cols, key=lambda c: df[c].dropna().astype(str).str.len().mean())
            logger.warning(f"No standard text column found, using: {text_col}")
        else:
            return [], ["No text column found. Expected columns: review, text, comment, feedback"]

    records: list[dict] = []

    for idx, row in df.iterrows():
        try:
            text = str(row[text_col]).strip() if pd.notna(row[text_col]) else ""
            if not text or text.lower() in ("nan", "none", ""):
                continue

            # Parse date
            parsed_date: Optional[datetime] = None
            if date_col and pd.notna(row.get(date_col)):
                try:
                    parsed_date = pd.to_datetime(row[date_col], errors="coerce")
                    if pd.isna(parsed_date):
                        parsed_date = None
                    else:
                        parsed_date = parsed_date.to_pydatetime()
                except Exception:
                    parsed_date = None

            records.append({
                "text": text,
                "date": parsed_date,
                "product_id": str(row[product_col]).strip() if product_col and pd.notna(row.get(product_col)) else None,
                "branch_id":  str(row[branch_col]).strip()  if branch_col  and pd.notna(row.get(branch_col))  else None,
                "source":     str(row[source_col]).strip()  if source_col  and pd.notna(row.get(source_col))  else "csv",
                "rating":     float(row[rating_col])        if rating_col  and pd.notna(row.get(rating_col))  else None,
            })

        except Exception as e:
            errors.append(f"Row {idx + 2}: {e}")
            if len(errors) > 50:
                errors.append("Too many errors — stopping row error collection")
                break

    logger.info(f"Parsed {len(records)} records from {filename}, {len(errors)} errors")
    return records, errors
