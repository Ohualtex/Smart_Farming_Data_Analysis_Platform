"""
/api/health/deep Endpoint Tests
=================================
Smoke tests for the deep health probe.

---

/api/health/deep ucu için temel testler.
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

    def test_uptime_component_present(self, client):
        """v3-7: uptime bileşeni eklendi, uptime_seconds >= 0 olmalı."""
        resp = client.get("/api/health/deep")
        uptime = resp.json()["components"].get("uptime")
        assert uptime is not None
        assert uptime["status"] == "ok"
        assert isinstance(uptime["uptime_seconds"], int)
        assert uptime["uptime_seconds"] >= 0
        assert "started_at" in uptime


class TestPrometheusMetrics:
    """v3-7: GET /api/health/metrics — Prometheus text exposition format."""

    def test_metrics_returns_200_with_text_plain(self, client):
        resp = client.get("/api/health/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers.get("content-type", "")

    def test_metrics_contains_required_gauges(self, client):
        resp = client.get("/api/health/metrics")
        body = resp.text
        # Beklenen metric isimleri ve HELP/TYPE etiketleri
        assert "sfdap_uptime_seconds" in body
        assert "sfdap_active_sensors" in body
        assert "sfdap_readings_last_hour" in body
        assert "sfdap_alerts_unresolved" in body
        # Prometheus format işaretleri
        assert "# HELP" in body
        assert "# TYPE" in body

    def test_alert_labels_present(self, client):
        resp = client.get("/api/health/metrics")
        body = resp.text
        for severity in ("critical", "medium", "low"):
            assert f'severity="{severity}"' in body
