"""
/api/health/deep endpoint testleri
====================================
Mehmet'in Cycle 6 görevi için skeleton testler.
"""

from __future__ import annotations


class TestDeepHealth:
    def test_deep_health_returns_200(self, client):
        resp = client.get("/api/health/deep")
        assert resp.status_code == 200

    def test_deep_health_has_required_fields(self, client):
        resp = client.get("/api/health/deep")
        data = resp.json()
        for field in ("status", "service", "version", "components", "timestamp"):
            assert field in data, f"missing {field}"

    def test_components_include_db_scheduler_ml(self, client):
        resp = client.get("/api/health/deep")
        components = resp.json()["components"]
        for key in ("db", "scheduler", "ml_model"):
            assert key in components

    def test_db_component_status_ok(self, client):
        # Test DB in-memory ve fixture ile yaratılır → SELECT 1 başarılı
        resp = client.get("/api/health/deep")
        assert resp.json()["components"]["db"]["status"] == "ok"

    def test_no_auth_required(self):
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app) as c:
            resp = c.get("/api/health/deep")
            # Health endpoint'leri public olmalı
            assert resp.status_code == 200
