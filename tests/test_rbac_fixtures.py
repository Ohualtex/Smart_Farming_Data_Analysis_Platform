"""
RBAC Fixture Smoke Tests (REBUILD Faz 1 / Adım 6 doğrulama).

Yeni 5 fixture'ın (anon/farmer/developer/overseer/admin) çalıştığını,
her rolün doğru role değeri ve Bearer header'ı taşıdığını sabitler.
Asıl behaviour testleri Adım 16'da gelir (TestFarmerScope, vb.).
"""

from __future__ import annotations


class TestRoleFixtures:
    """Her rol fixture'ı doğru role + Bearer header üretiyor mu?"""

    def test_farmer_client_role(self, farmer_client):
        client, user = farmer_client
        assert user.role == "farmer"
        assert "Authorization" in client.headers
        r = client.get("/api/auth/me")
        assert r.status_code == 200
        assert r.json()["role"] == "farmer"
        assert r.json()["owned_farms_count"] == 0  # yeni farmer çiftliksiz

    def test_developer_client_role(self, developer_client):
        client, user = developer_client
        assert user.role == "developer"
        assert client.get("/api/auth/me").json()["role"] == "developer"

    def test_overseer_client_role(self, overseer_client):
        client, user = overseer_client
        assert user.role == "overseer"
        assert client.get("/api/auth/me").json()["role"] == "overseer"

    def test_admin_client_role(self, admin_client):
        client, user = admin_client
        assert user.role == "admin"
        assert client.get("/api/auth/me").json()["role"] == "admin"


class TestAnonClient:
    """anon_client header'sız çalışmalı — /me 401, /api/health 200."""

    def test_anon_no_authorization_header(self, anon_client):
        assert "Authorization" not in anon_client.headers
        # X-API-Key de yok
        assert "X-API-Key" not in anon_client.headers

    def test_anon_can_hit_public_endpoint(self, anon_client):
        r = anon_client.get("/api/health")
        assert r.status_code == 200

    def test_anon_blocked_from_authenticated_endpoint(self, anon_client):
        r = anon_client.get("/api/auth/me")
        assert r.status_code == 401
