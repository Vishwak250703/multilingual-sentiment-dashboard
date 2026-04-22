"""Tests for /api/v1/admin/* endpoints (users + audit logs)."""
import uuid
import pytest
from tests.conftest import auth


class TestListUsers:
    async def test_admin_can_list(self, client, admin_token, tenant):
        resp = await client.get("/api/v1/admin/users", headers=auth(admin_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_analyst_forbidden(self, client, analyst_token):
        resp = await client.get("/api/v1/admin/users", headers=auth(analyst_token))
        assert resp.status_code == 403

    async def test_viewer_forbidden(self, client, viewer_token):
        resp = await client.get("/api/v1/admin/users", headers=auth(viewer_token))
        assert resp.status_code == 403

    async def test_requires_auth(self, client):
        resp = await client.get("/api/v1/admin/users")
        assert resp.status_code == 401

    async def test_only_own_tenant_users_returned(self, client, admin_token, db, tenant):
        """Users from another tenant must not appear."""
        from app.models.tenant import Tenant
        from app.models.user import User
        from passlib.context import CryptContext

        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        other = Tenant(id=str(uuid.uuid4()), name="OtherCo", slug=f"oc-{uuid.uuid4().hex[:6]}")
        db.add(other)
        await db.commit()

        other_user = User(
            id=str(uuid.uuid4()),
            tenant_id=other.id,
            email=f"leak-{uuid.uuid4().hex[:6]}@other.com",
            full_name="Leaked User",
            hashed_password=pwd_ctx.hash("Test@Password1"),
            role="viewer",
        )
        db.add(other_user)
        await db.commit()

        resp = await client.get("/api/v1/admin/users", headers=auth(admin_token))
        assert resp.status_code == 200
        for u in resp.json():
            assert u["tenant_id"] == tenant.id


class TestCreateUser:
    async def test_admin_creates_user(self, client, admin_token, tenant):
        payload = {
            "email": f"new-{uuid.uuid4().hex[:6]}@test.com",
            "password": "NewUser@Pass1",
            "full_name": "New User",
            "role": "viewer",
            "tenant_id": tenant.id,
        }
        resp = await client.post("/api/v1/admin/users", json=payload, headers=auth(admin_token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == payload["email"]
        assert body["role"] == "viewer"

    async def test_duplicate_email_rejected(self, client, admin_token, admin_user, tenant):
        payload = {
            "email": admin_user["email"],
            "password": "NewUser@Pass1",
            "full_name": "Dupe",
            "role": "viewer",
            "tenant_id": tenant.id,
        }
        resp = await client.post("/api/v1/admin/users", json=payload, headers=auth(admin_token))
        assert resp.status_code == 400

    async def test_analyst_cannot_create(self, client, analyst_token, tenant):
        payload = {
            "email": f"x-{uuid.uuid4().hex[:6]}@test.com",
            "password": "Test@Password1",
            "full_name": "X",
            "role": "viewer",
            "tenant_id": tenant.id,
        }
        resp = await client.post("/api/v1/admin/users", json=payload, headers=auth(analyst_token))
        assert resp.status_code == 403


class TestUpdateUser:
    async def test_admin_updates_role(self, client, admin_token, db, tenant):
        from app.models.user import User
        from passlib.context import CryptContext

        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        u = User(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            email=f"upd-{uuid.uuid4().hex[:6]}@test.com",
            full_name="Update Me",
            hashed_password=pwd_ctx.hash("Test@Password1"),
            role="viewer",
        )
        db.add(u)
        await db.commit()

        resp = await client.patch(
            f"/api/v1/admin/users/{u.id}",
            json={"role": "analyst"},
            headers=auth(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "analyst"

    async def test_update_nonexistent(self, client, admin_token):
        resp = await client.patch(
            f"/api/v1/admin/users/{uuid.uuid4()}",
            json={"role": "analyst"},
            headers=auth(admin_token),
        )
        assert resp.status_code == 404

    async def test_analyst_cannot_update(self, client, analyst_token, db, tenant):
        from app.models.user import User
        from passlib.context import CryptContext

        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        u = User(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            email=f"anl-upd-{uuid.uuid4().hex[:6]}@test.com",
            full_name="T",
            hashed_password=pwd_ctx.hash("Test@Password1"),
            role="viewer",
        )
        db.add(u)
        await db.commit()

        resp = await client.patch(
            f"/api/v1/admin/users/{u.id}",
            json={"role": "admin"},
            headers=auth(analyst_token),
        )
        assert resp.status_code == 403


class TestDeleteUser:
    async def test_admin_deletes_user(self, client, admin_token, db, tenant):
        from app.models.user import User
        from passlib.context import CryptContext

        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        u = User(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            email=f"del-{uuid.uuid4().hex[:6]}@test.com",
            full_name="Delete Me",
            hashed_password=pwd_ctx.hash("Test@Password1"),
            role="viewer",
        )
        db.add(u)
        await db.commit()

        resp = await client.delete(f"/api/v1/admin/users/{u.id}", headers=auth(admin_token))
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

    async def test_cannot_delete_self(self, client, admin_token, admin_user):
        resp = await client.delete(
            f"/api/v1/admin/users/{admin_user['id']}",
            headers=auth(admin_token),
        )
        assert resp.status_code == 400

    async def test_delete_nonexistent(self, client, admin_token):
        resp = await client.delete(
            f"/api/v1/admin/users/{uuid.uuid4()}",
            headers=auth(admin_token),
        )
        assert resp.status_code == 404

    async def test_analyst_cannot_delete(self, client, analyst_token, db, tenant):
        from app.models.user import User
        from passlib.context import CryptContext

        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        u = User(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            email=f"anl-del-{uuid.uuid4().hex[:6]}@test.com",
            full_name="T",
            hashed_password=pwd_ctx.hash("Test@Password1"),
            role="viewer",
        )
        db.add(u)
        await db.commit()

        resp = await client.delete(f"/api/v1/admin/users/{u.id}", headers=auth(analyst_token))
        assert resp.status_code == 403

    async def test_cannot_delete_other_tenant_user(self, client, admin_token, db, tenant):
        from app.models.tenant import Tenant
        from app.models.user import User
        from passlib.context import CryptContext

        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        other = Tenant(id=str(uuid.uuid4()), name="OtherDel", slug=f"od-{uuid.uuid4().hex[:6]}")
        db.add(other)
        await db.commit()

        other_user = User(
            id=str(uuid.uuid4()),
            tenant_id=other.id,
            email=f"otherdel-{uuid.uuid4().hex[:6]}@other.com",
            full_name="Other",
            hashed_password=pwd_ctx.hash("Test@Password1"),
            role="viewer",
        )
        db.add(other_user)
        await db.commit()

        resp = await client.delete(
            f"/api/v1/admin/users/{other_user.id}",
            headers=auth(admin_token),
        )
        assert resp.status_code == 404


class TestAuditLogs:
    async def test_admin_can_list(self, client, admin_token):
        resp = await client.get("/api/v1/admin/audit-logs", headers=auth(admin_token))
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "page" in body
        assert "total_pages" in body

    async def test_pagination(self, client, admin_token):
        resp = await client.get(
            "/api/v1/admin/audit-logs?page=1&page_size=5",
            headers=auth(admin_token),
        )
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 5

    async def test_analyst_forbidden(self, client, analyst_token):
        resp = await client.get("/api/v1/admin/audit-logs", headers=auth(analyst_token))
        assert resp.status_code == 403

    async def test_viewer_forbidden(self, client, viewer_token):
        resp = await client.get("/api/v1/admin/audit-logs", headers=auth(viewer_token))
        assert resp.status_code == 403

    async def test_requires_auth(self, client):
        resp = await client.get("/api/v1/admin/audit-logs")
        assert resp.status_code == 401
