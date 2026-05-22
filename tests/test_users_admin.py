"""
Admin User Management Tests — REBUILD Faz 3.5
===============================================
`GET/POST/DELETE /api/auth/users` + `PATCH /api/auth/users/{id}/password`.

Kapsama matriksi:
    list           → admin 200 (password_hash yok, owned_farms_count var),
                     farmer 403, anon 401, role filtresi
    create         → admin 201 (rol seçili), dup email 409, kısa şifre 400, non-admin 403
    delete         → self 409, çiftliği olan 409, başarı 204, non-admin 403, 404
    password reset → admin 200 (yeni şifreyle login 200), non-admin 403, kısa 400
"""

from __future__ import annotations

import uuid

from app.models.models import Farm, User


def _email() -> str:
    return f"adminmgmt-{uuid.uuid4().hex[:8]}@x.test"


def _make_user(db, role: str = "farmer") -> User:
    """Doğrudan DB'ye bir kullanıcı ekle (hedef olarak kullanmak için)."""
    u = User(name=f"{role.title()} Hedef", email=_email(), password_hash="x", role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


# ─── LIST ──────────────────────────────────────────────────────


class TestListUsers:
    def test_admin_lists_all_users(self, admin_client, db):
        client, _admin = admin_client
        _make_user(db, "farmer")
        _make_user(db, "developer")
        resp = client.get("/api/auth/users")
        assert resp.status_code == 200
        data = resp.json()
        # En az admin + default-admin (conftest) + 2 yeni = 4
        assert len(data) >= 3
        # password_hash asla sızmamalı
        for item in data:
            assert "password_hash" not in item
            assert "owned_farms_count" in item

    def test_list_includes_owned_farms_count(self, admin_client, db):
        client, _admin = admin_client
        farmer = _make_user(db, "farmer")
        db.add(Farm(user_id=farmer.id, name="Ç1", region="Ege"))
        db.add(Farm(user_id=farmer.id, name="Ç2", region="Ege"))
        db.commit()
        data = client.get("/api/auth/users").json()
        row = next(r for r in data if r["id"] == farmer.id)
        assert row["owned_farms_count"] == 2

    def test_list_role_filter(self, admin_client, db):
        client, _admin = admin_client
        _make_user(db, "developer")
        resp = client.get("/api/auth/users?role=developer")
        assert resp.status_code == 200
        assert all(r["role"] == "developer" for r in resp.json())

    def test_farmer_cannot_list_403(self, farmer_client):
        client, _user = farmer_client
        assert client.get("/api/auth/users").status_code == 403

    def test_anon_cannot_list_401(self, anon_client):
        assert anon_client.get("/api/auth/users").status_code == 401


# ─── GET single ────────────────────────────────────────────────


class TestGetUser:
    def test_admin_gets_single_user(self, admin_client, db):
        client, _admin = admin_client
        target = _make_user(db, "overseer")
        resp = client.get(f"/api/auth/users/{target.id}")
        assert resp.status_code == 200
        assert resp.json()["role"] == "overseer"
        assert "password_hash" not in resp.json()

    def test_get_missing_404(self, admin_client):
        client, _admin = admin_client
        assert client.get("/api/auth/users/999999").status_code == 404

    def test_farmer_cannot_get_403(self, farmer_client, db):
        client, _user = farmer_client
        target = _make_user(db, "farmer")
        assert client.get(f"/api/auth/users/{target.id}").status_code == 403


# ─── CREATE ────────────────────────────────────────────────────


class TestCreateUser:
    def test_admin_creates_user_with_role(self, admin_client):
        client, _admin = admin_client
        email = _email()
        resp = client.post(
            "/api/auth/users",
            json={"name": "Yeni Dev", "email": email, "password": "GuvenliP4ss", "role": "developer"},
        )
        assert resp.status_code == 201
        assert resp.json()["role"] == "developer"
        assert resp.json()["email"] == email

    def test_create_duplicate_email_409(self, admin_client, db):
        client, _admin = admin_client
        existing = _make_user(db, "farmer")
        resp = client.post(
            "/api/auth/users",
            json={"name": "Çakışan", "email": existing.email, "password": "GuvenliP4ss", "role": "farmer"},
        )
        assert resp.status_code == 409

    def test_create_short_password_400(self, admin_client):
        client, _admin = admin_client
        resp = client.post(
            "/api/auth/users",
            json={"name": "Kısa", "email": _email(), "password": "123", "role": "farmer"},
        )
        assert resp.status_code == 400

    def test_create_invalid_role_422(self, admin_client):
        client, _admin = admin_client
        resp = client.post(
            "/api/auth/users",
            json={"name": "Geçersiz", "email": _email(), "password": "GuvenliP4ss", "role": "superuser"},
        )
        assert resp.status_code == 422

    def test_farmer_cannot_create_403(self, farmer_client):
        client, _user = farmer_client
        resp = client.post(
            "/api/auth/users",
            json={"name": "X", "email": _email(), "password": "GuvenliP4ss", "role": "farmer"},
        )
        assert resp.status_code == 403


# ─── PASSWORD RESET ────────────────────────────────────────────


class TestAdminResetPassword:
    def test_admin_resets_password_then_login(self, admin_client, db):
        client, _admin = admin_client
        # Gerçek login için register ile kullanıcı oluştur (bcrypt hash)
        email = _email()
        client.post("/api/auth/register", json={"name": "Reset Hedef", "email": email, "password": "EskiP4ss2026"})
        target = db.query(User).filter(User.email == email).first()
        resp = client.patch(f"/api/auth/users/{target.id}/password", json={"new_password": "YeniP4ss2026"})
        assert resp.status_code == 200
        # Yeni şifreyle login olabilmeli
        login = client.post("/api/auth/login", json={"email": email, "password": "YeniP4ss2026"})
        assert login.status_code == 200

    def test_reset_short_password_400(self, admin_client, db):
        client, _admin = admin_client
        target = _make_user(db, "farmer")
        resp = client.patch(f"/api/auth/users/{target.id}/password", json={"new_password": "123"})
        assert resp.status_code == 400

    def test_reset_missing_user_404(self, admin_client):
        client, _admin = admin_client
        assert client.patch("/api/auth/users/999999/password", json={"new_password": "GecerliP4ss"}).status_code == 404

    def test_farmer_cannot_reset_403(self, farmer_client, db):
        client, _user = farmer_client
        target = _make_user(db, "farmer")
        resp = client.patch(f"/api/auth/users/{target.id}/password", json={"new_password": "GecerliP4ss"})
        assert resp.status_code == 403


# ─── DELETE ────────────────────────────────────────────────────


class TestDeleteUser:
    def test_admin_deletes_user_204(self, admin_client, db):
        client, _admin = admin_client
        target = _make_user(db, "farmer")
        resp = client.delete(f"/api/auth/users/{target.id}")
        assert resp.status_code == 204
        assert db.query(User).filter(User.id == target.id).first() is None

    def test_admin_cannot_delete_self_409(self, admin_client):
        client, admin = admin_client
        resp = client.delete(f"/api/auth/users/{admin.id}")
        assert resp.status_code == 409

    def test_cannot_delete_user_with_farms_409(self, admin_client, db):
        client, _admin = admin_client
        farmer = _make_user(db, "farmer")
        db.add(Farm(user_id=farmer.id, name="Çiftlik", region="Ege"))
        db.commit()
        resp = client.delete(f"/api/auth/users/{farmer.id}")
        assert resp.status_code == 409
        # Hâlâ duruyor olmalı
        assert db.query(User).filter(User.id == farmer.id).first() is not None

    def test_delete_missing_404(self, admin_client):
        client, _admin = admin_client
        assert client.delete("/api/auth/users/999999").status_code == 404

    def test_farmer_cannot_delete_403(self, farmer_client, db):
        client, _user = farmer_client
        target = _make_user(db, "farmer")
        assert client.delete(f"/api/auth/users/{target.id}").status_code == 403

    def test_anon_cannot_delete_401(self, anon_client, db):
        target = _make_user(db, "farmer")
        assert anon_client.delete(f"/api/auth/users/{target.id}").status_code == 401
