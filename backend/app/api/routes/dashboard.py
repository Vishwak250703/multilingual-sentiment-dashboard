from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, cast, Float
from typing import Optional
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.schemas.dashboard import (
    DashboardData, KPIData, SentimentTrend, TrendPoint,
    LanguageDistribution, SourceBreakdown, AspectSentiment, InsightItem,
)
from app.models.review import Review
from app.models.user import User
from app.services.nlp.language_detector import get_language_name

router = APIRouter()


def _period_to_delta(period: str) -> timedelta:
    return {
        "1d": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
    }.get(period, timedelta(days=7))


async def _compute_kpis(
    db: AsyncSession,
    tenant_id: str,
    since: datetime,
    prev_since: datetime,
) -> KPIData:
    # Current period aggregates
    current_q = await db.execute(
        select(
            func.count(Review.id).label("total"),
            func.avg(Review.sentiment_score).label("avg_score"),
            func.count(func.distinct(Review.detected_language)).label("langs"),
        ).where(
            and_(
                Review.tenant_id == tenant_id,
                Review.created_at >= since,
                Review.processing_status == "completed",
            )
        )
    )
    row = current_q.one()
    total = row.total or 0
    avg_score = float(row.avg_score or 0.0)
    langs = row.langs or 0

    # Sentiment counts
    sent_q = await db.execute(
        select(Review.sentiment, func.count(Review.id)).where(
            and_(
                Review.tenant_id == tenant_id,
                Review.created_at >= since,
                Review.processing_status == "completed",
                Review.sentiment.isnot(None),
            )
        ).group_by(Review.sentiment)
    )
    sent_counts = {r[0]: r[1] for r in sent_q.all()}
    pos = sent_counts.get("positive", 0)
    neg = sent_counts.get("negative", 0)
    neu = sent_counts.get("neutral", 0)
    denom = max(total, 1)

    # Previous period avg_score for delta
    prev_q = await db.execute(
        select(func.avg(Review.sentiment_score)).where(
            and_(
                Review.tenant_id == tenant_id,
                Review.created_at >= prev_since,
                Review.created_at < since,
                Review.processing_status == "completed",
            )
        )
    )
    prev_score = float(prev_q.scalar() or 0.0)
    delta_score = round(avg_score - prev_score, 3)

    return KPIData(
        total_reviews=total,
        overall_sentiment_score=round(avg_score, 3),
        positive_percent=round(pos / denom * 100, 1),
        negative_percent=round(neg / denom * 100, 1),
        neutral_percent=round(neu / denom * 100, 1),
        active_languages=langs,
        change_from_last_period={"sentiment_score": delta_score},
    )


async def _compute_trend(
    db: AsyncSession,
    tenant_id: str,
    since: datetime,
    period: str,
) -> SentimentTrend:
    # Pull all completed reviews in period (only needed columns)
    q = await db.execute(
        select(
            Review.created_at,
            Review.sentiment,
            Review.sentiment_score,
        ).where(
            and_(
                Review.tenant_id == tenant_id,
                Review.created_at >= since,
                Review.processing_status == "completed",
                Review.sentiment_score.isnot(None),
            )
        ).order_by(Review.created_at)
    )
    rows = q.all()

    # Bucket by day (or week for 90d)
    use_weekly = period == "90d"
    buckets: dict[str, list] = defaultdict(list)
    for created_at, sentiment, score in rows:
        if use_weekly:
            # ISO week start (Monday)
            day = created_at.date()
            bucket = str(day - timedelta(days=day.weekday()))
        else:
            bucket = str(created_at.date())
        buckets[bucket].append((sentiment, score))

    points: list[TrendPoint] = []
    for date_str in sorted(buckets.keys()):
        entries = buckets[date_str]
        scores = [s for _, s in entries if s is not None]
        avg = sum(scores) / len(scores) if scores else 0.0
        pos_c = sum(1 for s, _ in entries if s == "positive")
        neg_c = sum(1 for s, _ in entries if s == "negative")
        neu_c = sum(1 for s, _ in entries if s == "neutral")
        points.append(TrendPoint(
            date=date_str,
            sentiment_score=round(avg, 3),
            positive_count=pos_c,
            negative_count=neg_c,
            neutral_count=neu_c,
            total=len(entries),
        ))

    return SentimentTrend(points=points, period=period)


async def _compute_language_dist(
    db: AsyncSession,
    tenant_id: str,
    since: datetime,
) -> list[LanguageDistribution]:
    q = await db.execute(
        select(Review.detected_language, func.count(Review.id).label("cnt")).where(
            and_(
                Review.tenant_id == tenant_id,
                Review.created_at >= since,
                Review.processing_status == "completed",
                Review.detected_language.isnot(None),
            )
        ).group_by(Review.detected_language).order_by(func.count(Review.id).desc())
    )
    rows = q.all()
    total = sum(r.cnt for r in rows) or 1
    return [
        LanguageDistribution(
            language=r.detected_language,
            language_name=get_language_name(r.detected_language),
            count=r.cnt,
            percent=round(r.cnt / total * 100, 1),
        )
        for r in rows
    ]


async def _compute_source_breakdown(
    db: AsyncSession,
    tenant_id: str,
    since: datetime,
) -> list[SourceBreakdown]:
    q = await db.execute(
        select(
            Review.source,
            func.count(Review.id).label("cnt"),
            func.avg(Review.sentiment_score).label("avg_score"),
        ).where(
            and_(
                Review.tenant_id == tenant_id,
                Review.created_at >= since,
                Review.processing_status == "completed",
            )
        ).group_by(Review.source).order_by(func.count(Review.id).desc())
    )
    rows = q.all()
    total = sum(r.cnt for r in rows) or 1
    return [
        SourceBreakdown(
            source=r.source,
            count=r.cnt,
            percent=round(r.cnt / total * 100, 1),
            sentiment_score=round(float(r.avg_score or 0.0), 3),
        )
        for r in rows
    ]


async def _compute_aspects_and_keywords(
    db: AsyncSession,
    tenant_id: str,
    since: datetime,
) -> tuple[list[AspectSentiment], list[dict]]:
    """Fetch aspects+keywords JSON and aggregate in Python."""
    q = await db.execute(
        select(Review.aspects, Review.keywords).where(
            and_(
                Review.tenant_id == tenant_id,
                Review.created_at >= since,
                Review.processing_status == "completed",
            )
        )
    )
    rows = q.all()

    # Aspects: {aspect: {sentiment: count, score_sum: float}}
    aspect_data: dict[str, dict] = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0, "score_sum": 0.0, "total": 0})
    keyword_counter: Counter = Counter()

    sentiment_score_map = {"positive": 0.8, "negative": -0.8, "neutral": 0.0}

    for aspects, keywords in rows:
        if aspects and isinstance(aspects, dict):
            for aspect, sentiment_val in aspects.items():
                if isinstance(sentiment_val, str) and sentiment_val in ("positive", "negative", "neutral"):
                    aspect_data[aspect][sentiment_val] += 1
                    aspect_data[aspect]["score_sum"] += sentiment_score_map[sentiment_val]
                    aspect_data[aspect]["total"] += 1
                elif isinstance(sentiment_val, dict):
                    s = sentiment_val.get("sentiment", "neutral")
                    if s in ("positive", "negative", "neutral"):
                        aspect_data[aspect][s] += 1
                        aspect_data[aspect]["score_sum"] += sentiment_score_map.get(s, 0.0)
                        aspect_data[aspect]["total"] += 1

        if keywords and isinstance(keywords, list):
            for kw in keywords:
                if isinstance(kw, str) and kw.strip():
                    keyword_counter[kw.lower().strip()] += 1

    # Build AspectSentiment list
    aspect_results: list[AspectSentiment] = []
    for aspect, data in aspect_data.items():
        total = data["total"]
        if total == 0:
            continue
        dominant = max(["positive", "negative", "neutral"], key=lambda s: data[s])
        score = round(data["score_sum"] / total, 3)
        aspect_results.append(AspectSentiment(
            aspect=aspect,
            sentiment=dominant,
            score=score,
            count=total,
        ))
    aspect_results.sort(key=lambda x: x.count, reverse=True)

    # Build top keywords list (top 20)
    top_kw = [
        {"keyword": kw, "count": cnt, "sentiment": "neutral"}
        for kw, cnt in keyword_counter.most_common(20)
    ]

    return aspect_results, top_kw


# ─── Routes ────────────────────────────────────────────────────────────────────

@router.get("/", response_model=DashboardData)
async def get_dashboard(
    period: str = Query("7d", description="Time period: 1d, 7d, 30d, 90d"),
    product_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    source: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return full dashboard data for the current tenant."""
    now = datetime.now(timezone.utc)
    delta = _period_to_delta(period)
    since = now - delta
    prev_since = since - delta
    tenant_id = current_user.tenant_id

    kpis = await _compute_kpis(db, tenant_id, since, prev_since)
    trend = await _compute_trend(db, tenant_id, since, period)
    lang_dist = await _compute_language_dist(db, tenant_id, since)
    src_breakdown = await _compute_source_breakdown(db, tenant_id, since)
    aspects, keywords = await _compute_aspects_and_keywords(db, tenant_id, since)

    return DashboardData(
        kpis=kpis,
        trend=trend,
        language_distribution=lang_dist,
        source_breakdown=src_breakdown,
        aspect_sentiments=aspects,
        top_keywords=keywords,
        insights=[],  # served from /insights/ endpoint
    )


@router.get("/kpis", response_model=KPIData)
async def get_kpis(
    period: str = Query("7d"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """KPI cards data only — for lightweight polling."""
    now = datetime.now(timezone.utc)
    delta = _period_to_delta(period)
    since = now - delta
    prev_since = since - delta
    return await _compute_kpis(db, current_user.tenant_id, since, prev_since)


@router.get("/trend", response_model=SentimentTrend)
async def get_trend(
    period: str = Query("7d"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Sentiment trend over time."""
    now = datetime.now(timezone.utc)
    since = now - _period_to_delta(period)
    return await _compute_trend(db, current_user.tenant_id, since, period)
