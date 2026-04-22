"""Tests for /api/v1/reviews/* endpoints."""
import uuid
import pytest
from tests.conftest import auth


async def _make_review(db, tenant_id: str, sentiment: str = "positive", source: str = "csv"):
    from app.models.review import Review

    r = Review(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        raw_text="This product is great and I love it!",
        translated_text="This product is great and I love it!",
        original_language="en",
        detected_language="en",
        source=source,
        sentiment=sentiment,
        sentiment_score=0.7 if sentiment == "positive" else -0.7 if sentiment == "negative" else 0.0,
        confidence=0.88,
        processing_status="completed",
        keywords=["great", "love"],
        aspects={"quality": "positive"},
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


class TestReviewsList:
    async def test_list_returns_paginated(self, client, admin_token, db, tenant):
        for _ in range(5):
            await _make_review(db, tenant.id)
        resp = await client.get("/api/v1/reviews/", headers=auth(admin_token))
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] >= 5

    async def test_filter_by_sentiment(self, client, admin_token, db, tenant):
        await _make_review(db, tenant.id, sentiment="negative")
        resp = await client.get("/api/v1/reviews/?sentiment=negative", headers=auth(admin_token))
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["sentiment"] == "negative"

    async def test_filter_by_source(self, client, admin_token, db, tenant):
        await _make_review(db, tenant.id, source="app_review")
        resp = await client.get("/api/v1/reviews/?source=app_review", headers=auth(admin_token))
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["source"] == "app_review"

    async def test_pagination(self, client, admin_token, db, tenant):
        for _ in range(5):
            await _make_review(db, tenant.id)
        resp = await client.get("/api/v1/reviews/?page=1&page_size=2", headers=auth(admin_token))
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 2

    async def test_requires_auth(self, client):
        resp = await client.get("/api/v1/reviews/")
        assert resp.status_code == 401


class TestReviewDetail:
    async def test_get_own_review(self, client, admin_token, db, tenant):
        r = await _make_review(db, tenant.id)
        resp = await client.get(f"/api/v1/reviews/{r.id}", headers=auth(admin_token))
        assert resp.status_code == 200
        assert resp.json()["id"] == r.id

    async def test_get_nonexistent(self, client, admin_token):
        resp = await client.get(f"/api/v1/reviews/{uuid.uuid4()}", headers=auth(admin_token))
        assert resp.status_code == 404

    async def test_cannot_access_other_tenant_review(self, client, db, admin_token, tenant):
        from app.models.tenant import Tenant
        other = Tenant(id=str(uuid.uuid4()), name="Other", slug=f"o-{uuid.uuid4().hex[:6]}")
        db.add(other)
        await db.commit()
        r = await _make_review(db, other.id)
        resp = await client.get(f"/api/v1/reviews/{r.id}", headers=auth(admin_token))
        assert resp.status_code == 404  # isolation — not found for this tenant


class TestCorrectSentiment:
    async def test_analyst_can_correct(self, client, analyst_token, db, tenant):
        r = await _make_review(db, tenant.id, sentiment="positive")
        resp = await client.post(
            f"/api/v1/reviews/{r.id}/correct",
            json={"corrected_sentiment": "negative", "note": "Actually negative"},
            headers=auth(analyst_token),
        )
        assert resp.status_code == 200
        assert resp.json()["corrected_sentiment"] == "negative"

    async def test_admin_can_correct(self, client, admin_token, db, tenant):
        r = await _make_review(db, tenant.id)
        resp = await client.post(
            f"/api/v1/reviews/{r.id}/correct",
            json={"corrected_sentiment": "neutral"},
            headers=auth(admin_token),
        )
        assert resp.status_code == 200

    async def test_viewer_cannot_correct(self, client, viewer_token, db, tenant):
        r = await _make_review(db, tenant.id)
        resp = await client.post(
            f"/api/v1/reviews/{r.id}/correct",
            json={"corrected_sentiment": "negative"},
            headers=auth(viewer_token),
        )
        assert resp.status_code == 403

    async def test_invalid_sentiment_value(self, client, analyst_token, db, tenant):
        r = await _make_review(db, tenant.id)
        resp = await client.post(
            f"/api/v1/reviews/{r.id}/correct",
            json={"corrected_sentiment": "very_bad"},
            headers=auth(analyst_token),
        )
        assert resp.status_code == 422


class TestExport:
    async def test_csv_export(self, client, admin_token, db, tenant):
        for _ in range(3):
            await _make_review(db, tenant.id)
        resp = await client.get("/api/v1/reviews/export", headers=auth(admin_token))
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        content = resp.content.decode()
        assert "sentiment" in content  # header row present

    async def test_pdf_export(self, client, admin_token, db, tenant):
        await _make_review(db, tenant.id)
        resp = await client.get("/api/v1/reviews/export/pdf", headers=auth(admin_token))
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers["content-type"]
        # PDF magic bytes: %PDF
        assert resp.content[:4] == b"%PDF"

    async def test_export_filtered(self, client, admin_token, db, tenant):
        await _make_review(db, tenant.id, sentiment="negative")
        resp = await client.get(
            "/api/v1/reviews/export?sentiment=negative",
            headers=auth(admin_token),
        )
        assert resp.status_code == 200
        lines = resp.content.decode().splitlines()
        # All data rows (skip header) should be negative
        for line in lines[1:]:
            assert "negative" in line.lower()
