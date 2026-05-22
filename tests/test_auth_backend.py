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

    def test_register_short_password_rejected(self, client):
        """Kısa şifre 4xx döner.

        Eskiden 422 kontrol ediliyordu; 422'nin FastAPI auto-üretilen
        şeması `list[ValidationError]` beklediği için düz-string detail
        OpenAPI kontrat doğrulamasını kırıyordu, handler 400'e çevrildi.

        ---

        Plain-string `detail` is incompatible with FastAPI's auto-
        generated 422 envelope, so the handler now returns 400. Test
        accepts either to stay forgiving of future changes.
        """
        resp = client.post(
            "/api/auth/register",
            json={"name": "Short", "email": _new_email(), "password": "1234"},
        )
        assert resp.status_code in (400, 422)

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

    def test_me_without_token_401(self, anon_client):
        # anon_client tamamen header'sız — Authorization yok → 401
        resp = anon_client.get("/api/auth/me")
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


class TestChangePassword:
    """PATCH /api/auth/me/password — REBUILD Faz 2 / Adım 9."""

    def _register_and_login(self, client, password: str = "oldpass1234"):  # noqa: S107 — test fixture, sentinel
        email = _new_email()
        client.post(
            "/api/auth/register",
            json={"name": "PW User", "email": email, "password": password},
        )
        token = client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        ).json()["access_token"]
        return email, token

    def test_change_password_success_200(self, client):
        email, token = self._register_and_login(client)
        resp = client.patch(
            "/api/auth/me/password",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": "oldpass1234", "new_password": "newpass5678"},
        )
        assert resp.status_code == 200
        # Eski şifre artık geçmez, yeni şifre geçer
        old_login = client.post("/api/auth/login", json={"email": email, "password": "oldpass1234"})
        assert old_login.status_code == 401
        new_login = client.post("/api/auth/login", json={"email": email, "password": "newpass5678"})
        assert new_login.status_code == 200

    def test_change_password_wrong_current_401(self, client):
        _email, token = self._register_and_login(client)
        resp = client.patch(
            "/api/auth/me/password",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": "yanlış", "new_password": "yenisifre1234"},
        )
        assert resp.status_code == 401

    def test_change_password_too_short_400(self, client):
        _email, token = self._register_and_login(client)
        resp = client.patch(
            "/api/auth/me/password",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": "oldpass1234", "new_password": "kisa"},
        )
        assert resp.status_code == 400

    def test_change_password_same_as_current_400(self, client):
        _email, token = self._register_and_login(client)
        resp = client.patch(
            "/api/auth/me/password",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": "oldpass1234", "new_password": "oldpass1234"},
        )
        assert resp.status_code == 400

    def test_change_password_without_token_401(self, anon_client):
        resp = anon_client.patch(
            "/api/auth/me/password",
            json={"current_password": "x", "new_password": "yenisifre1234"},
        )
        assert resp.status_code == 401
