import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.config import settings
from app.schemas.dashboard import InsightItem, AspectSentiment
from app.models.review import Review
from app.models.user import User

import anthropic
from anthropic import Anthropic

router = APIRouter()

_claude_client: Anthropic | None = None


def _get_claude() -> Anthropic:
    global _claude_client
    if _claude_client is None:
        _claude_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _claude_client


def _period_to_delta(period: str) -> timedelta:
    return {"1d": timedelta(days=1), "7d": timedelta(days=7),
            "30d": timedelta(days=30), "90d": timedelta(days=90)}.get(period, timedelta(days=7))


@router.get("/", response_model=List[InsightItem])
async def get_insights(
    period: str = Query("7d"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Call Claude with aggregated stats → 3-5 insight bullets."""
    now = datetime.now(timezone.utc)
    since = now - _period_to_delta(period)
    tenant_id = current_user.tenant_id

    # Gather stats for Claude
    q = await db.execute(
        select(
            func.count(Review.id).label("total"),
            func.avg(Review.sentiment_score).label("avg_score"),
        ).where(
            and_(
                Review.tenant_id == tenant_id,
                Review.created_at >= since,
                Review.processing_status == "completed",
            )
        )
    )
    row = q.one()
    total = row.total or 0
    avg_score = float(row.avg_score or 0.0)

    if total == 0:
        return [InsightItem(
            type="trend",
            title="No data yet",
            description="Upload reviews or push data via API to see AI-generated insights here.",
            severity="info",
        )]

    # Sentiment distribution
    sent_q = await db.execute(
        select(Review.sentiment, func.count(Review.id)).where(
            and_(Review.tenant_id == tenant_id, Review.created_at >= since,
                 Review.processing_status == "completed", Review.sentiment.isnot(None))
        ).group_by(Review.sentiment)
    )
    sent_counts = {r[0]: r[1] for r in sent_q.all()}

    # Top sources
    src_q = await db.execute(
        select(Review.source, func.count(Review.id).label("cnt"),
               func.avg(Review.sentiment_score).label("avg")).where(
            and_(Review.tenant_id == tenant_id, Review.created_at >= since,
                 Review.processing_status == "completed")
        ).group_by(Review.source).order_by(func.count(Review.id).desc()).limit(5)
    )
    sources = [{"source": r[0], "count": r[1], "avg_score": round(float(r[2] or 0), 2)} for r in src_q.all()]

    # Top aspects
    asp_q = await db.execute(
        select(Review.aspects).where(
            and_(Review.tenant_id == tenant_id, Review.created_at >= since,
                 Review.processing_status == "completed", Review.aspects.isnot(None))
        ).limit(500)
    )
    aspect_counts: dict[str, dict] = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0})
    for (aspects,) in asp_q.all():
        if aspects and isinstance(aspects, dict):
            for asp, sent in aspects.items():
                s = sent if isinstance(sent, str) else (sent.get("sentiment") if isinstance(sent, dict) else None)
                if s in ("positive", "negative", "neutral"):
                    aspect_counts[asp][s] += 1

    top_aspects = sorted(
        [{"aspect": a, **v} for a, v in aspect_counts.items()],
        key=lambda x: x["negative"], reverse=True
    )[:5]

    # Top keywords
    kw_q = await db.execute(
        select(Review.keywords).where(
            and_(Review.tenant_id == tenant_id, Review.created_at >= since,
                 Review.processing_status == "completed", Review.keywords.isnot(None))
        ).limit(300)
    )
    from collections import Counter
    kw_counter: Counter = Counter()
    for (kws,) in kw_q.all():
        if kws and isinstance(kws, list):
            kw_counter.update(kw.lower().strip() for kw in kws if isinstance(kw, str))
    top_keywords = [kw for kw, _ in kw_counter.most_common(10)]

    # Call Claude
    stats_summary = {
        "period": period,
        "total_reviews": total,
        "avg_sentiment_score": round(avg_score, 2),
        "sentiment_distribution": sent_counts,
        "top_sources": sources,
        "top_negative_aspects": top_aspects,
        "top_keywords": top_keywords,
    }

    prompt = f"""You are an expert customer experience analyst. Analyze this review data summary and generate 3-5 concise, actionable business insights.

Data Summary:
{json.dumps(stats_summary, indent=2)}

Return a JSON array of insight objects. Each object must have:
- type: one of "trend", "spike", "keyword", "aspect"
- title: short title (max 8 words)
- description: 1-2 sentence actionable insight
- severity: one of "info", "warning", "critical"

Rules:
- "critical" only for strongly negative patterns (avg_score < -0.3 or >40% negative)
- "warning" for mild negatives or declining trends
- "info" for neutral observations or positive highlights
- Be specific, reference actual numbers from the data
- Focus on what the business should act on

Return ONLY the JSON array, no markdown, no explanation."""

    try:
        response = _get_claude().messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
        return [InsightItem(**item) for item in parsed if isinstance(item, dict)]
    except Exception:
        # Fallback: rule-based insights
        insights = []
        neg_pct = sent_counts.get("negative", 0) / max(total, 1) * 100
        pos_pct = sent_counts.get("positive", 0) / max(total, 1) * 100

        if neg_pct > 40:
            insights.append(InsightItem(
                type="spike",
                title="High negative sentiment detected",
                description=f"{neg_pct:.0f}% of reviews in this period are negative. Immediate investigation recommended.",
                severity="critical",
            ))
        elif neg_pct > 25:
            insights.append(InsightItem(
                type="trend",
                title="Rising negative feedback",
                description=f"{neg_pct:.0f}% negative reviews — above typical thresholds. Monitor closely.",
                severity="warning",
            ))

        if pos_pct > 60:
            insights.append(InsightItem(
                type="trend",
                title="Strong positive sentiment",
                description=f"{pos_pct:.0f}% positive reviews across {total} submissions. Customer satisfaction is high.",
                severity="info",
            ))

        if top_keywords:
            insights.append(InsightItem(
                type="keyword",
                title="Top recurring themes",
                description=f"Most frequent keywords: {', '.join(top_keywords[:5])}.",
                severity="info",
            ))

        return insights or [InsightItem(
            type="trend",
            title="Sentiment analysis complete",
            description=f"Analyzed {total} reviews with average score {avg_score:.2f}.",
            severity="info",
        )]


@router.get("/aspects", response_model=List[AspectSentiment])
async def get_aspect_sentiments(
    period: str = Query("7d"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Aspect-based sentiment breakdown."""
    now = datetime.now(timezone.utc)
    since = now - _period_to_delta(period)
    tenant_id = current_user.tenant_id

    q = await db.execute(
        select(Review.aspects).where(
            and_(Review.tenant_id == tenant_id, Review.created_at >= since,
                 Review.processing_status == "completed", Review.aspects.isnot(None))
        )
    )
    aspect_data: dict[str, dict] = defaultdict(
        lambda: {"positive": 0, "negative": 0, "neutral": 0, "score_sum": 0.0, "total": 0}
    )
    score_map = {"positive": 0.8, "negative": -0.8, "neutral": 0.0}

    for (aspects,) in q.all():
        if aspects and isinstance(aspects, dict):
            for aspect, val in aspects.items():
                s = val if isinstance(val, str) else (val.get("sentiment") if isinstance(val, dict) else None)
                if s in ("positive", "negative", "neutral"):
                    aspect_data[aspect][s] += 1
                    aspect_data[aspect]["score_sum"] += score_map[s]
                    aspect_data[aspect]["total"] += 1

    results = []
    for aspect, data in aspect_data.items():
        t = data["total"]
        if t == 0:
            continue
        dominant = max(["positive", "negative", "neutral"], key=lambda x: data[x])
        results.append(AspectSentiment(
            aspect=aspect,
            sentiment=dominant,
            score=round(data["score_sum"] / t, 3),
            count=t,
        ))
    results.sort(key=lambda x: x.count, reverse=True)
    return results
