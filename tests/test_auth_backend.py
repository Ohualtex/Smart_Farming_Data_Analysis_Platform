"""
Auth Backend Tests
====================
Covers the `app/routers/auth.py` flow — register, login, me, logout —
plus the relevant edge cases (bcrypt hash, JWT validation, blacklist).

---

`app/routers/auth.py` için register/login/me/logout akışı ve edge case'ler.
"""

from __future__ import annotations

import uuid


def _new_email() -> str:
    return f"test-{uuid.uuid4().hex[:8]}@sfdap.test"


class TestRegister:
    def test_register_creates_user(self, client):
        email = _new_email()
        resp = client.post(
            "/api/auth/register",
            json={
                "name": "Test User",
                "email": email,
                "password": "testpass1234",
                "phone": "05551234567",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == email
        assert data["role"] == "farmer"
        assert "id" in data
        # Şifre asla response'a sızmamalı
        assert "password" not in data
        assert "password_hash" not in data

    def test_register_short_password_returns_422(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"name": "Short", "email": _new_email(), "password": "1234"},
        )
        assert resp.status_code == 422

    def test_register_duplicate_email_returns_409(self, client):
        email = _new_email()
        payload = {"name": "Test", "email": email, "password": "validpass1234"}
        first = client.post("/api/auth/register", json=payload)
        assert first.status_code == 201
        second = client.post("/api/auth/register", json=payload)
        assert second.status_code == 409

    def test_register_missing_field_422(self, client):
        # email eksik
        resp = client.post("/api/auth/register", json={"name": "X", "password": "validpass1234"})
        assert resp.status_code == 422


class TestLogin:
    def test_login_returns_token(self, client):
        email = _new_email()
        client.post("/api/auth/register", json={"name": "T", "email": email, "password": "validpass1234"})
        resp = client.post("/api/auth/login", json={"email": email, "password": "validpass1234"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        assert len(data["access_token"]) > 20  # token urlsafe(32) ≈ 43 char

    def test_login_wrong_password_401(self, client):
        email = _new_email()
        client.post("/api/auth/register", json={"name": "T", "email": email, "password": "rightpass123"})
        resp = client.post("/api/auth/login", json={"email": email, "password": "wrongpass"})
        assert resp.status_code == 401

    def test_login_unknown_user_401(self, client):
        resp = client.post("/api/auth/login", json={"email": _new_email(), "password": "anything12345"})
        assert resp.status_code == 401


class TestMe:
    def test_me_with_valid_token(self, client):
        email = _new_email()
        client.post("/api/auth/register", json={"name": "T", "email": email, "password": "validpass1234"})
        token = client.post(
            "/api/auth/login",
            json={"email": email, "password": "validpass1234"},
        ).json()["access_token"]
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["email"] == email

    def test_me_without_token_401(self, client):
        # client fixture X-API-Key gönderiyor ama Authorization header'ı yok
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token_401(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer fake-invalid-token"})
        assert resp.status_code == 401

    def test_me_malformed_authorization_header_401(self, client):
        # "Bearer " prefix'i yok
        resp = client.get("/api/auth/me", headers={"Authorization": "JustSomeToken"})
        assert resp.status_code == 401


class TestLogout:
    def test_logout_invalidates_token(self, client):
        email = _new_email()
        client.post("/api/auth/register", json={"name": "T", "email": email, "password": "validpass1234"})
        token = client.post(
            "/api/auth/login",
            json={"email": email, "password": "validpass1234"},
        ).json()["access_token"]
        # Token geçerli
        assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200
        # Logout
        logout = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert logout.status_code == 204
        # Artık geçersiz
        assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401

    def test_logout_idempotent(self, client):
        # Token olmadan logout — error vermesin
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 204
