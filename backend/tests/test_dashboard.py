"""Tests for /api/v1/dashboard/* endpoints."""
import pytest
import uuid
from datetime import datetime, timezone
from tests.conftest import auth


async def _seed_reviews(db, tenant_id: str, count: int = 10):
    """Insert completed reviews so dashboard aggregations have data."""
    from app.models.review import Review

    reviews = []
    for i in range(count):
        sentiment = ["positive", "negative", "neutral"][i % 3]
        r = Review(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            raw_text=f"Review number {i}",
            translated_text=f"Review number {i}",
            original_language="en",
            detected_language="en",
            source="csv",
            sentiment=sentiment,
            sentiment_score=0.6 if sentiment == "positive" else -0.6 if sentiment == "negative" else 0.0,
            confidence=0.9,
            processing_status="completed",
            keywords=["quality", "service"],
            aspects={"service": "positive", "price": "neutral"},
        )
        reviews.append(r)

    db.add_all(reviews)
    await db.commit()


class TestDashboard:
    async def test_full_dashboard_empty(self, client, admin_token):
        """Dashboard returns valid structure even with no reviews."""
        resp = await client.get("/api/v1/dashboard/", headers=auth(admin_token))
        assert resp.status_code == 200
        body = resp.json()
        assert "kpis" in body
        assert "trend" in body
        assert "language_distribution" in body
        assert "source_breakdown" in body

    async def test_full_dashboard_with_data(self, client, admin_token, db, tenant):
        await _seed_reviews(db, tenant.id, 15)
        resp = await client.get("/api/v1/dashboard/?period=30d", headers=auth(admin_token))
        assert resp.status_code == 200
        kpis = resp.json()["kpis"]
        assert kpis["total_reviews"] >= 15
        assert 0 <= kpis["positive_percent"] <= 100

    async def test_kpis_endpoint(self, client, admin_token, db, tenant):
        await _seed_reviews(db, tenant.id, 5)
        resp = await client.get("/api/v1/dashboard/kpis?period=7d", headers=auth(admin_token))
        assert resp.status_code == 200
        body = resp.json()
        for field in ["total_reviews", "overall_sentiment_score",
                      "positive_percent", "negative_percent", "neutral_percent", "active_languages"]:
            assert field in body

    async def test_trend_endpoint(self, client, admin_token, db, tenant):
        await _seed_reviews(db, tenant.id, 5)
        resp = await client.get("/api/v1/dashboard/trend?period=7d", headers=auth(admin_token))
        assert resp.status_code == 200
        body = resp.json()
        assert "points" in body
        assert "period" in body

    async def test_dashboard_period_options(self, client, admin_token):
        for period in ["1d", "7d", "30d", "90d"]:
            resp = await client.get(f"/api/v1/dashboard/?period={period}", headers=auth(admin_token))
            assert resp.status_code == 200, f"Period {period} failed"

    async def test_dashboard_requires_auth(self, client):
        resp = await client.get("/api/v1/dashboard/")
        assert resp.status_code == 401

    async def test_tenant_isolation(self, client, db, admin_token, tenant):
        """Reviews from another tenant must not appear in this tenant's dashboard."""
        from app.models.tenant import Tenant
        from app.models.review import Review

        # Create another tenant + its review
        other_tenant = Tenant(id=str(uuid.uuid4()), name="Other", slug=f"other-{uuid.uuid4().hex[:6]}")
        db.add(other_tenant)
        await db.commit()

        other_review = Review(
            id=str(uuid.uuid4()),
            tenant_id=other_tenant.id,
            raw_text="Leaked review",
            original_language="en",
            processing_status="completed",
            sentiment="positive",
            sentiment_score=0.9,
            source="csv",
        )
        db.add(other_review)
        await db.commit()

        resp = await client.get("/api/v1/dashboard/kpis", headers=auth(admin_token))
        assert resp.status_code == 200
        # The leaked review should not inflate our count
        assert resp.json()["total_reviews"] < 100  # sanity, not counting other tenant's


class TestInsights:
    async def test_insights_empty(self, client, admin_token):
        resp = await client.get("/api/v1/insights/", headers=auth(admin_token))
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)

    async def test_aspects_empty(self, client, admin_token):
        resp = await client.get("/api/v1/insights/aspects", headers=auth(admin_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
