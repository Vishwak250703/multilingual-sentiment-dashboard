from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class ReviewOut(BaseModel):
    id: str
    tenant_id: str
    raw_text: str
    translated_text: Optional[str] = None
    original_language: str
    detected_language: Optional[str] = None
    source: str
    product_id: Optional[str] = None
    branch_id: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    confidence: Optional[float] = None
    sentence_sentiments: Optional[List[Dict]] = None
    aspects: Optional[Dict[str, str]] = None
    keywords: Optional[List[str]] = None
    is_pii_masked: bool
    processing_status: str
    review_date: Optional[datetime] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReviewFilter(BaseModel):
    language: Optional[str] = None
    sentiment: Optional[str] = None
    source: Optional[str] = None
    product_id: Optional[str] = None
    branch_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = 1
    page_size: int = 20


class ReviewPaginated(BaseModel):
    items: List[ReviewOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class HumanReviewCreate(BaseModel):
    corrected_sentiment: str
    note: Optional[str] = None


class HumanReviewOut(BaseModel):
    id: str
    review_id: str
    analyst_id: str
    original_sentiment: Optional[str]
    corrected_sentiment: str
    note: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
