"""
Sistem Uyarı (SystemAlert) endpoint testleri
=============================================
Ecenur'un Cycle 6 görevi için skeleton testler.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_alert_payload():
    return {
        "farm_id": 1,
        "alert_type": "sensor_anomaly",
        "severity": "medium",
        "message": "Sensör 5 son 2 saatte veri göndermedi.",
    }


class TestAlertsList:
    def test_list_empty_returns_200(self, client):
        resp = client.get("/api/alerts/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_after_create(self, client, sample_alert_payload):
        client.post("/api/alerts/", json=sample_alert_payload)
        resp = client.get("/api/alerts/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["alert_type"] == "sensor_anomaly"
        assert data[0]["is_resolved"] is False

    def test_list_filter_by_severity(self, client, sample_alert_payload):
        client.post("/api/alerts/", json=sample_alert_payload)
        critical = {**sample_alert_payload, "severity": "critical"}
        client.post("/api/alerts/", json=critical)
        resp = client.get("/api/alerts/?severity=critical")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["severity"] == "critical"

    def test_list_filter_by_resolved(self, client, sample_alert_payload):
        r1 = client.post("/api/alerts/", json=sample_alert_payload)
        client.patch(f"/api/alerts/{r1.json()['id']}", json={"is_resolved": True})
        client.post("/api/alerts/", json=sample_alert_payload)  # 2. unresolved
        resp = client.get("/api/alerts/?is_resolved=false")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


class TestAlertCreate:
    def test_create_returns_201(self, client, sample_alert_payload):
        resp = client.post("/api/alerts/", json=sample_alert_payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] > 0
        assert data["is_resolved"] is False
        assert "created_at" in data

    def test_create_without_auth_returns_401(self, sample_alert_payload):
        # Yeni client, header'sız
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app) as c:
            resp = c.post("/api/alerts/", json=sample_alert_payload)
            assert resp.status_code == 401

    def test_create_validation_error_returns_422(self, client):
        # alert_type ve message zorunlu
        resp = client.post("/api/alerts/", json={"severity": "low"})
        assert resp.status_code == 422


class TestAlertGet:
    def test_get_existing(self, client, sample_alert_payload):
        created = client.post("/api/alerts/", json=sample_alert_payload).json()
        resp = client.get(f"/api/alerts/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_nonexistent_returns_404(self, client):
        resp = client.get("/api/alerts/99999")
        assert resp.status_code == 404


class TestAlertUpdate:
    def test_resolve_alert(self, client, sample_alert_payload):
        created = client.post("/api/alerts/", json=sample_alert_payload).json()
        resp = client.patch(f"/api/alerts/{created['id']}", json={"is_resolved": True})
        assert resp.status_code == 200
        assert resp.json()["is_resolved"] is True

    def test_partial_update_severity(self, client, sample_alert_payload):
        created = client.post("/api/alerts/", json=sample_alert_payload).json()
        resp = client.patch(f"/api/alerts/{created['id']}", json={"severity": "critical"})
        assert resp.status_code == 200
        assert resp.json()["severity"] == "critical"
        assert resp.json()["is_resolved"] is False  # değişmedi

    def test_update_nonexistent_returns_404(self, client):
        resp = client.patch("/api/alerts/99999", json={"is_resolved": True})
        assert resp.status_code == 404
