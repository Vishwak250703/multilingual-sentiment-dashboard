from pydantic import BaseModel
from typing import List, Dict, Optional, Any


class KPIData(BaseModel):
    total_reviews: int
    overall_sentiment_score: float
    positive_percent: float
    negative_percent: float
    neutral_percent: float
    active_languages: int
    change_from_last_period: Optional[Dict[str, float]] = None


class TrendPoint(BaseModel):
    date: str
    sentiment_score: float
    positive_count: int
    negative_count: int
    neutral_count: int
    total: int


class SentimentTrend(BaseModel):
    points: List[TrendPoint]
    period: str  # daily | weekly | monthly


class LanguageDistribution(BaseModel):
    language: str
    language_name: str
    count: int
    percent: float


class SourceBreakdown(BaseModel):
    source: str
    count: int
    percent: float
    sentiment_score: float


class AspectSentiment(BaseModel):
    aspect: str
    sentiment: str
    score: float
    count: int


class InsightItem(BaseModel):
    type: str  # trend | spike | keyword | aspect
    title: str
    description: str
    severity: str  # info | warning | critical
    metadata: Optional[Dict[str, Any]] = None


class DashboardData(BaseModel):
    kpis: KPIData
    trend: SentimentTrend
    language_distribution: List[LanguageDistribution]
    source_breakdown: List[SourceBreakdown]
    aspect_sentiments: List[AspectSentiment]
    top_keywords: List[Dict[str, Any]]
    insights: List[InsightItem]
