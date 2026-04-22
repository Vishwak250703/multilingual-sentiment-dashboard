import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Float, JSON, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Raw content
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_language: Mapped[str] = mapped_column(String(10), default="en")
    detected_language: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Source metadata
    source: Mapped[str] = mapped_column(String(50), default="csv")
    # csv | api | webhook | app_review | social | chat_log | support_ticket
    product_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    branch_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Sentiment results
    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # positive | negative | neutral
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # -1.0 to 1.0
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 0.0 to 1.0
    sentence_sentiments: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # [{"sentence": "...", "sentiment": "positive", "score": 0.9}]

    # Aspect-Based Sentiment
    aspects: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # {"price": "positive", "delivery": "negative", "service": "neutral"}

    # Keywords / highlights
    keywords: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # ["late delivery", "bad service"]

    # PII masking
    is_pii_masked: Mapped[bool] = mapped_column(default=False)

    # Processing status
    processing_status: Mapped[str] = mapped_column(String(30), default="pending")
    # pending | processing | completed | failed

    # Timestamps
    review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="reviews")  # noqa
    human_reviews: Mapped[list["HumanReview"]] = relationship("HumanReview", back_populates="review")  # noqa

    __table_args__ = (
        Index("ix_reviews_tenant_sentiment", "tenant_id", "sentiment"),
        Index("ix_reviews_tenant_source", "tenant_id", "source"),
        Index("ix_reviews_tenant_created", "tenant_id", "created_at"),
    )
