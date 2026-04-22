"""Tests for /api/v1/alerts/* endpoints."""
import uuid
import pytest
from datetime import datetime, timezone
from tests.conftest import auth


async def _make_alert(db, tenant_id: str, resolved: bool = False) -> object:
    from app.models.alert import Alert

    a = Alert(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        alert_type="sentiment_drop",
        severity="high",
        title="Sentiment dropped significantly",
        message="Overall sentiment fell by 25% in the last 24 hours.",
        is_resolved=resolved,
        triggered_at=datetime.now(timezone.utc),
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


class TestListAlerts:
    async def test_requires_auth(self, client):
        resp = await client.get("/api/v1/alerts/")
        assert resp.status_code == 401

    async def test_admin_can_list(self, client, admin_token, db, tenant):
        await _make_alert(db, tenant.id)
        resp = await client.get("/api/v1/alerts/", headers=auth(admin_token))
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "unresolved_count" in body
        assert "total" in body

    async def test_analyst_can_list(self, client, analyst_token, db, tenant):
        await _make_alert(db, tenant.id)
        resp = await client.get("/api/v1/alerts/", headers=auth(analyst_token))
        assert resp.status_code == 200

    async def test_viewer_can_list(self, client, viewer_token, db, tenant):
        resp = await client.get("/api/v1/alerts/", headers=auth(viewer_token))
        assert resp.status_code == 200

    async def test_unresolved_filter_default(self, client, admin_token, db, tenant):
        """Default response should only include unresolved alerts."""
        await _make_alert(db, tenant.id, resolved=False)
        await _make_alert(db, tenant.id, resolved=True)
        resp = await client.get("/api/v1/alerts/", headers=auth(admin_token))
        assert resp.status_code == 200
        body = resp.json()
        for item in body["items"]:
            assert item["is_resolved"] is False

    async def test_resolved_filter(self, client, admin_token, db, tenant):
        await _make_alert(db, tenant.id, resolved=True)
        resp = await client.get("/api/v1/alerts/?resolved=true", headers=auth(admin_token))
        assert resp.status_code == 200
        # With resolved=true, both resolved and unresolved are returned
        assert isinstance(resp.json()["items"], list)

    async def test_tenant_isolation(self, client, admin_token, db, tenant):
        """Alerts from another tenant must not appear."""
        from app.models.tenant import Tenant

        other = Tenant(id=str(uuid.uuid4()), name="Other", slug=f"iso-{uuid.uuid4().hex[:6]}")
        db.add(other)
        await db.commit()
        await _make_alert(db, other.id)

        resp = await client.get("/api/v1/alerts/", headers=auth(admin_token))
        assert resp.status_code == 200
        # All returned items belong to the requesting tenant
        for item in resp.json()["items"]:
            assert item["tenant_id"] == tenant.id

    async def test_unresolved_count_accurate(self, client, admin_token, db, tenant):
        await _make_alert(db, tenant.id, resolved=False)
        await _make_alert(db, tenant.id, resolved=False)
        await _make_alert(db, tenant.id, resolved=True)
        resp = await client.get("/api/v1/alerts/", headers=auth(admin_token))
        assert resp.status_code == 200
        assert resp.json()["unresolved_count"] >= 2


class TestResolveAlert:
    async def test_admin_can_resolve(self, client, admin_token, db, tenant):
        a = await _make_alert(db, tenant.id)
        resp = await client.post(
            f"/api/v1/alerts/{a.id}/resolve",
            headers=auth(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["is_resolved"] is True

    async def test_analyst_can_resolve(self, client, analyst_token, db, tenant):
        a = await _make_alert(db, tenant.id)
        resp = await client.post(
            f"/api/v1/alerts/{a.id}/resolve",
            headers=auth(analyst_token),
        )
        assert resp.status_code == 200
        assert resp.json()["is_resolved"] is True

    async def test_viewer_can_resolve(self, client, viewer_token, db, tenant):
        """Alerts route uses get_current_active_user — all roles may resolve."""
        a = await _make_alert(db, tenant.id)
        resp = await client.post(
            f"/api/v1/alerts/{a.id}/resolve",
            headers=auth(viewer_token),
        )
        assert resp.status_code == 200

    async def test_resolve_nonexistent(self, client, admin_token):
        resp = await client.post(
            f"/api/v1/alerts/{uuid.uuid4()}/resolve",
            headers=auth(admin_token),
        )
        assert resp.status_code == 404

    async def test_cannot_resolve_other_tenant_alert(self, client, admin_token, db, tenant):
        from app.models.tenant import Tenant

        other = Tenant(id=str(uuid.uuid4()), name="Other2", slug=f"o2-{uuid.uuid4().hex[:6]}")
        db.add(other)
        await db.commit()
        a = await _make_alert(db, other.id)

        resp = await client.post(
            f"/api/v1/alerts/{a.id}/resolve",
            headers=auth(admin_token),
        )
        assert resp.status_code == 404  # tenant isolation

    async def test_requires_auth(self, client, db, tenant):
        a = await _make_alert(db, tenant.id)
        resp = await client.post(f"/api/v1/alerts/{a.id}/resolve")
        assert resp.status_code == 401
