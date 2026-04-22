from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional
import math
import csv
import io
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.auth import get_current_active_user, require_analyst
from app.schemas.review import ReviewPaginated, ReviewOut, HumanReviewCreate, HumanReviewOut, ReviewFilter
from app.models.review import Review
from app.models.human_review import HumanReview
from app.models.user import User
import uuid

router = APIRouter()


@router.get("/", response_model=ReviewPaginated)
async def list_reviews(
    language: Optional[str] = None,
    sentiment: Optional[str] = None,
    source: Optional[str] = None,
    product_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List reviews with filters and pagination."""
    filters = [Review.tenant_id == current_user.tenant_id]
    if language:
        filters.append(Review.detected_language == language)
    if sentiment:
        filters.append(Review.sentiment == sentiment)
    if source:
        filters.append(Review.source == source)
    if product_id:
        filters.append(Review.product_id == product_id)
    if branch_id:
        filters.append(Review.branch_id == branch_id)
    if date_from:
        try:
            filters.append(Review.review_date >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            filters.append(Review.review_date <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    count_q = await db.execute(select(func.count()).select_from(Review).where(and_(*filters)))
    total = count_q.scalar()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(Review).where(and_(*filters))
        .order_by(Review.created_at.desc())
        .offset(offset).limit(page_size)
    )
    items = result.scalars().all()

    return ReviewPaginated(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total else 1,
    )


@router.get("/export")
async def export_reviews_csv(
    language: Optional[str] = None,
    sentiment: Optional[str] = None,
    source: Optional[str] = None,
    product_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Export filtered reviews as a CSV file (max 10 000 rows)."""
    filters = [Review.tenant_id == current_user.tenant_id]
    if language:
        filters.append(Review.detected_language == language)
    if sentiment:
        filters.append(Review.sentiment == sentiment)
    if source:
        filters.append(Review.source == source)
    if product_id:
        filters.append(Review.product_id == product_id)
    if branch_id:
        filters.append(Review.branch_id == branch_id)
    if date_from:
        try:
            filters.append(Review.review_date >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            filters.append(Review.review_date <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    result = await db.execute(
        select(Review).where(and_(*filters))
        .order_by(Review.created_at.desc())
        .limit(10_000)
    )
    reviews = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "review_date", "source", "language", "sentiment",
        "sentiment_score", "confidence", "product_id", "branch_id",
        "status", "review_text", "keywords",
    ])
    for r in reviews:
        writer.writerow([
            r.id,
            str(r.review_date or r.created_at)[:10],
            r.source,
            r.detected_language or r.original_language,
            r.sentiment or "",
            round(r.sentiment_score, 4) if r.sentiment_score is not None else "",
            round(r.confidence, 4) if r.confidence is not None else "",
            r.product_id or "",
            r.branch_id or "",
            r.processing_status,
            (r.translated_text or r.raw_text)[:500].replace("\n", " "),
            ", ".join(r.keywords) if r.keywords else "",
        ])

    output.seek(0)
    filename = f"reviews_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/pdf")
async def export_reviews_pdf(
    language: Optional[str] = None,
    sentiment: Optional[str] = None,
    source: Optional[str] = None,
    product_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Export filtered reviews as a PDF report (max 500 rows)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, HRFlowable,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    filters = [Review.tenant_id == current_user.tenant_id]
    if language:
        filters.append(Review.detected_language == language)
    if sentiment:
        filters.append(Review.sentiment == sentiment)
    if source:
        filters.append(Review.source == source)
    if product_id:
        filters.append(Review.product_id == product_id)
    if branch_id:
        filters.append(Review.branch_id == branch_id)
    if date_from:
        try:
            filters.append(Review.review_date >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            filters.append(Review.review_date <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    # Aggregate KPIs
    kpi_q = await db.execute(
        select(
            func.count(Review.id).label("total"),
            func.avg(Review.sentiment_score).label("avg_score"),
            func.sum(func.cast(Review.sentiment == "positive", func.Integer())).label("pos"),
            func.sum(func.cast(Review.sentiment == "negative", func.Integer())).label("neg"),
            func.sum(func.cast(Review.sentiment == "neutral",  func.Integer())).label("neu"),
        ).where(and_(*filters))
    )
    kpi = kpi_q.one()
    total = kpi.total or 0
    avg_score = float(kpi.avg_score or 0.0)
    pos = int(kpi.pos or 0)
    neg = int(kpi.neg or 0)
    neu = int(kpi.neu or 0)

    # Reviews (capped at 500)
    result = await db.execute(
        select(Review).where(and_(*filters))
        .order_by(Review.created_at.desc())
        .limit(500)
    )
    reviews = result.scalars().all()

    # ── Build PDF in memory ────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    # Colour palette (dark theme — works fine on white paper with adjusted bg)
    PURPLE = colors.HexColor("#7c3aed")
    DARK   = colors.HexColor("#1e1b2e")
    LIGHT  = colors.HexColor("#f5f3ff")
    GREY   = colors.HexColor("#6b7280")
    GREEN  = colors.HexColor("#10b981")
    RED    = colors.HexColor("#ef4444")
    SLATE  = colors.HexColor("#94a3b8")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title", parent=styles["Title"],
        fontSize=20, textColor=PURPLE, spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontSize=10, textColor=GREY, spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Normal"],
        fontSize=12, textColor=DARK, fontName="Helvetica-Bold",
        spaceBefore=14, spaceAfter=6,
    )
    cell_style = ParagraphStyle(
        "Cell", parent=styles["Normal"],
        fontSize=8, textColor=DARK, leading=11,
    )

    story = []

    # Title
    generated = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
    story.append(Paragraph("Sentiment Analysis Report", title_style))
    story.append(Paragraph(f"Generated {generated}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PURPLE, spaceAfter=12))

    # KPI summary table
    story.append(Paragraph("Summary", section_style))
    score_color = GREEN if avg_score >= 0.1 else RED if avg_score <= -0.1 else SLATE
    kpi_data = [
        ["Metric", "Value"],
        ["Total Reviews", str(total)],
        ["Avg Sentiment Score", f"{avg_score:+.3f}"],
        ["Positive Reviews", f"{pos}  ({pos / total * 100:.1f}%)" if total else "0"],
        ["Negative Reviews", f"{neg}  ({neg / total * 100:.1f}%)" if total else "0"],
        ["Neutral Reviews",  f"{neu}  ({neu / total * 100:.1f}%)" if total else "0"],
    ]
    kpi_table = Table(kpi_data, colWidths=[80 * mm, 80 * mm])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), PURPLE),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 9),
        ("BACKGROUND",   (0, 1), (-1, -1), LIGHT),
        ("FONTSIZE",     (0, 1), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("PADDING",      (0, 0), (-1, -1), 7),
        ("TEXTCOLOR",    (1, 2), (1, 2), score_color),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 10))

    # Reviews table
    if reviews:
        story.append(Paragraph(f"Reviews ({len(reviews)} shown, newest first)", section_style))
        headers = ["Date", "Source", "Lang", "Sentiment", "Score", "Review Text"]
        col_widths = [22 * mm, 22 * mm, 12 * mm, 20 * mm, 16 * mm, None]
        # remaining width for text column
        used = sum(w for w in col_widths if w)
        available = A4[0] - 30 * mm  # page width minus margins
        col_widths[-1] = available - used

        table_data = [headers]
        for r in reviews:
            sentiment = r.sentiment or "—"
            score = f"{r.sentiment_score:+.2f}" if r.sentiment_score is not None else "—"
            text = (r.translated_text or r.raw_text or "")[:160].replace("\n", " ")
            date_str = str(r.review_date or r.created_at)[:10]
            table_data.append([
                date_str,
                (r.source or "—")[:12],
                (r.detected_language or r.original_language or "—")[:5],
                sentiment.capitalize(),
                score,
                Paragraph(text, cell_style),
            ])

        rev_table = Table(table_data, colWidths=col_widths, repeatRows=1)

        def _sent_color(s: str):
            if s == "Positive": return GREEN
            if s == "Negative": return RED
            return SLATE

        style_cmds = [
            ("BACKGROUND",  (0, 0), (-1, 0), PURPLE),
            ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, 0), 8),
            ("FONTSIZE",    (0, 1), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
            ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
            ("VALIGN",      (0, 0), (-1, -1), "TOP"),
            ("PADDING",     (0, 0), (-1, -1), 5),
            ("WORDWRAP",    (5, 1), (5, -1), True),
        ]
        # Colour sentiment column per row
        for row_i, r in enumerate(reviews, start=1):
            sent = (r.sentiment or "").capitalize()
            c = _sent_color(sent)
            style_cmds.append(("TEXTCOLOR", (3, row_i), (3, row_i), c))

        rev_table.setStyle(TableStyle(style_cmds))
        story.append(rev_table)

    doc.build(story)
    buf.seek(0)

    filename = f"sentiment_report_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{review_id}", response_model=ReviewOut)
async def get_review(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(Review).where(Review.id == review_id, Review.tenant_id == current_user.tenant_id)
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.post("/{review_id}/correct", response_model=HumanReviewOut)
async def correct_review(
    review_id: str,
    body: HumanReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """Human analyst corrects the sentiment label."""
    result = await db.execute(
        select(Review).where(Review.id == review_id, Review.tenant_id == current_user.tenant_id)
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    hr = HumanReview(
        id=str(uuid.uuid4()),
        review_id=review_id,
        analyst_id=current_user.id,
        original_sentiment=review.sentiment,
        corrected_sentiment=body.corrected_sentiment,
        note=body.note,
    )
    db.add(hr)

    # Update the review's sentiment
    review.sentiment = body.corrected_sentiment
    return hr
