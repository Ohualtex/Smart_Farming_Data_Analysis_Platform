"""
System Alert Endpoint Tests
=============================
Smoke tests for the SystemAlert CRUD endpoints.

---

SystemAlert CRUD uçları için temel testler.
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


# ─── REBUILD Faz 5 — POST /api/alerts/check (otomatik tarama) ────────────
class TestAlertsCheck:
    """Tarla tarama → düşük nem / hastalık hatırlatması üretimi (dedup'lı, rol-aware)."""

    def _seed_field(self, db, user_id, moisture=None, disease_recent=False, name="Tarla"):
        from datetime import UTC, datetime, timedelta

        from app.models.models import (
            Farm,
            Field,
            PlantHealthImage,
            Sensor,
            SoilMoistureReading,
        )

        farm = Farm(user_id=user_id, name=f"{name} Çiftlik", region="Ege")
        db.add(farm)
        db.flush()
        field = Field(farm_id=farm.id, name=name, soil_type="killi")
        db.add(field)
        db.flush()
        if moisture is not None:
            sensor = Sensor(field_id=field.id, sensor_type="soil_moisture", serial_number=f"SN-{field.id}")
            db.add(sensor)
            db.flush()
            db.add(
                SoilMoistureReading(
                    sensor_id=sensor.id,
                    moisture_percent=moisture,
                    reading_timestamp=datetime.now(UTC) - timedelta(hours=1),
                )
            )
        if disease_recent:
            db.add(
                PlantHealthImage(
                    field_id=field.id,
                    image_url="x.jpg",
                    captured_at=datetime.now(UTC) - timedelta(days=1),
                    diagnosis="healthy",
                )
            )
        db.commit()
        return field.id

    def test_check_creates_low_moisture_alert(self, farmer_client, db):
        client, user = farmer_client
        self._seed_field(db, user.id, moisture=18.0, disease_recent=True, name="Susuz")
        resp = client.post("/api/alerts/check")
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] >= 1
        types = [a["alert_type"] for a in data["alerts"]]
        assert "low_moisture" in types
        # %18 < 20 → critical
        lm = next(a for a in data["alerts"] if a["alert_type"] == "low_moisture")
        assert lm["severity"] == "critical"

    def test_check_is_idempotent_dedup(self, farmer_client, db):
        client, user = farmer_client
        self._seed_field(db, user.id, moisture=25.0, disease_recent=True)
        first = client.post("/api/alerts/check").json()
        assert first["created"] >= 1
        second = client.post("/api/alerts/check").json()
        # Aynı açık alert tekrar üretilmez
        assert second["created"] == 0

    def test_check_disease_reminder(self, farmer_client, db):
        client, user = farmer_client
        # Nem yok (low_moisture tetiklenmez), hastalık analizi de yok → reminder
        self._seed_field(db, user.id, moisture=None, disease_recent=False)
        data = client.post("/api/alerts/check").json()
        types = [a["alert_type"] for a in data["alerts"]]
        assert "disease_reminder" in types

    def test_check_no_alert_for_healthy_field(self, farmer_client, db):
        client, user = farmer_client
        # Yüksek nem + yakın hastalık analizi → uyarı yok
        self._seed_field(db, user.id, moisture=55.0, disease_recent=True)
        data = client.post("/api/alerts/check").json()
        assert data["created"] == 0

    def test_check_overseer_forbidden_403(self, overseer_client):
        client, _ = overseer_client
        assert client.post("/api/alerts/check").status_code == 403

    def test_check_batch_multiple_fields_v3_3(self, farmer_client, db):
        """v4-1 coverage: v3-3 N+1 fix (batch GROUP BY) çoklu field senaryosu.

        Önceki N+1 yapı her field için iki ek query yapıyordu. Yeni batch path
        tek GROUP BY ile çalışır; sonuç eşdeğer olmalı (3 field, 3 düşük nem
        + 3 hastalık reminder = 6 alert, dedup öncesi). 1 alert iki tarafta da
        üretilir (low_moisture + disease_reminder) per field.
        """
        client, user = farmer_client
        # 3 tarla — hepsi susuz + hastalık analizi eski (yok)
        ids = [self._seed_field(db, user.id, moisture=15.0, name=f"BatchTarla{i}") for i in range(3)]
        assert len(ids) == 3
        resp = client.post("/api/alerts/check")
        assert resp.status_code == 200
        data = resp.json()
        # Her field'da iki alert tipi: low_moisture + disease_reminder → 6
        assert data["created"] == 6
        types_count = dict.fromkeys(("low_moisture", "disease_reminder"), 0)
        for a in data["alerts"]:
            if a["alert_type"] in types_count:
                types_count[a["alert_type"]] += 1
        assert types_count["low_moisture"] == 3
        assert types_count["disease_reminder"] == 3

    def test_check_empty_fields_returns_zero(self, farmer_client):
        """v4-1: farmer'ın hiç field'ı yoksa batch query None döner, 0 alert."""
        client, _ = farmer_client
        resp = client.post("/api/alerts/check")
        assert resp.status_code == 200
        assert resp.json()["created"] == 0

    def test_check_anon_401(self, anon_client):
        assert anon_client.post("/api/alerts/check").status_code == 401

    def test_check_farmer_scope_only_own(self, farmer_client, db):
        client, user = farmer_client
        # Başka kullanıcının susuz tarlası — taranmamalı
        self._seed_field(db, 9999, moisture=10.0, disease_recent=True, name="Başka")
        data = client.post("/api/alerts/check").json()
        assert data["checked_fields"] == 0
        assert data["created"] == 0
