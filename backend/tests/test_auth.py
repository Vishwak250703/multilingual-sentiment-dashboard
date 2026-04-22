"""Tests for /api/v1/auth/* endpoints."""
import pytest
from tests.conftest import auth


class TestLogin:
    async def test_login_success(self, client, admin_user):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": admin_user["email"], "password": admin_user["password"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    async def test_login_wrong_password(self, client, admin_user):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": admin_user["email"], "password": "WrongPass!99"},
        )
        assert resp.status_code == 401

    async def test_login_unknown_email(self, client):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "nobody@test.com", "password": "Test@Password1"},
        )
        assert resp.status_code == 401

    async def test_login_missing_fields(self, client):
        resp = await client.post("/api/v1/auth/login", data={"username": "x@x.com"})
        assert resp.status_code == 422


class TestMe:
    async def test_me_authenticated(self, client, admin_token, admin_user):
        resp = await client.get("/api/v1/auth/me", headers=auth(admin_token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == admin_user["email"]
        assert body["role"] == "admin"

    async def test_me_unauthenticated(self, client):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_me_bad_token(self, client):
        resp = await client.get("/api/v1/auth/me", headers=auth("invalid.token.here"))
        assert resp.status_code == 401


class TestRefresh:
    async def test_refresh_success(self, client, admin_user):
        login = await client.post(
            "/api/v1/auth/login",
            data={"username": admin_user["email"], "password": admin_user["password"]},
        )
        refresh_token = login.json()["refresh_token"]
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_refresh_invalid_token(self, client):
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "bogus"})
        assert resp.status_code == 401


class TestLogout:
    async def test_logout(self, client, admin_token):
        resp = await client.post("/api/v1/auth/logout", headers=auth(admin_token))
        assert resp.status_code == 200
