"""
Sensör Endpoint Testleri — REBUILD Faz 1 RBAC migration.

GET    /api/sensors/                — list (rol-aware)
POST   /api/sensors/                 — yeni sensör (farmer + admin; field ownership)
GET    /api/sensors/count
GET    /api/sensors/{id}             — detay (ownership)
DELETE /api/sensors/{id}             — sil (ownership + write yetki)
POST   /api/sensors/readings         — okuma ekle (sensor ownership)
GET    /api/sensors/{id}/readings    — okumalar (ownership)
GET    /api/sensors/{id}/readings    — okumalar (ownership)

Mevcut testler `admin_client` + ön-seed Farm/Field fixture ile migrate
edildi. RBAC behaviour testleri (farmer/overseer/anon) Adım 16'da
toplu olarak gelecek.
"""

from __future__ import annotations

import pytest

from app.models.models import Farm, Field


@pytest.fixture
def admin_with_field(admin_client, db):
    """Admin user + 1 farm + 1 field — sensör testleri için ortak seed.

    Sensor.field_id FK olduğundan testlerin geçerli bir field'a referans
    vermesi gerekir. Bu fixture admin'e bağlı bir field oluşturur ve
    `(client, field_id)` döner.
    """
    client, user = admin_client
    farm = Farm(user_id=user.id, name="Test Çiftlik", region="Marmara", city="İstanbul")
    db.add(farm)
    db.flush()
    field = Field(farm_id=farm.id, name="Test Tarla", soil_type="killi")
    db.add(field)
    db.commit()
    return client, field.id


def _sensor_payload(field_id: int, serial: str = "SENSOR-001", sensor_type: str = "soil_moisture") -> dict:
    return {
        "serial_number": serial,
        "sensor_type": sensor_type,
        "lat": 38.7225,
        "lng": 39.4900,
        "field_id": field_id,
    }


# ───── GET /api/sensors/ ──────────────────────────────────────────────────────
class TestGetSensors:
    def test_get_sensors_empty_returns_200(self, admin_with_field):
        client, _ = admin_with_field
        response = client.get("/api/sensors/")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_sensors_returns_list(self, admin_with_field):
        client, field_id = admin_with_field
        client.post("/api/sensors/", json=_sensor_payload(field_id))
        response = client.get("/api/sensors/")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_get_sensors_with_limit(self, admin_with_field):
        client, field_id = admin_with_field
        for i in range(3):
            client.post("/api/sensors/", json=_sensor_payload(field_id, serial=f"SENSOR-00{i}"))
        response = client.get("/api/sensors/?limit=2")
        assert len(response.json()) <= 2


# ───── POST /api/sensors/ ─────────────────────────────────────────────────────
class TestCreateSensor:
    def test_create_sensor_returns_201(self, admin_with_field):
        client, field_id = admin_with_field
        response = client.post("/api/sensors/", json=_sensor_payload(field_id))
        assert response.status_code == 201

    def test_create_sensor_response_has_id(self, admin_with_field):
        client, field_id = admin_with_field
        response = client.post("/api/sensors/", json=_sensor_payload(field_id))
        data = response.json()
        assert "id" in data
        assert data["id"] is not None

    def test_create_sensor_data_matches(self, admin_with_field):
        client, field_id = admin_with_field
        payload = _sensor_payload(field_id)
        response = client.post("/api/sensors/", json=payload)
        data = response.json()
        assert data["serial_number"] == payload["serial_number"]
        assert data["sensor_type"] == payload["sensor_type"]

    def test_create_sensor_missing_field_returns_422(self, admin_with_field):
        client, _ = admin_with_field
        invalid = {"sensor_type": "soil_moisture"}
        response = client.post("/api/sensors/", json=invalid)
        assert response.status_code == 422


# ───── GET /api/sensors/{id} ──────────────────────────────────────────────────
class TestGetSensorById:
    def test_get_existing_sensor(self, admin_with_field):
        client, field_id = admin_with_field
        created = client.post("/api/sensors/", json=_sensor_payload(field_id)).json()
        response = client.get(f"/api/sensors/{created['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_get_nonexistent_sensor_returns_404(self, admin_with_field):
        client, _ = admin_with_field
        response = client.get("/api/sensors/99999")
        assert response.status_code == 404

    def test_get_sensor_404_message(self, admin_with_field):
        client, _ = admin_with_field
        response = client.get("/api/sensors/99999")
        # v4-6 envelope (TR karakter): "bulunamadı" message/detail içinde
        body = response.json()
        assert "bulunamad" in body.get("detail", "").lower() or "bulunamad" in body.get("message", "").lower()


# ───── DELETE /api/sensors/{id} ───────────────────────────────────────────────
class TestDeleteSensor:
    def test_delete_existing_sensor(self, admin_with_field):
        client, field_id = admin_with_field
        created = client.post("/api/sensors/", json=_sensor_payload(field_id)).json()
        response = client.delete(f"/api/sensors/{created['id']}")
        assert response.status_code == 200

    def test_delete_removes_sensor(self, admin_with_field):
        client, field_id = admin_with_field
        created = client.post("/api/sensors/", json=_sensor_payload(field_id)).json()
        client.delete(f"/api/sensors/{created['id']}")
        response = client.get(f"/api/sensors/{created['id']}")
        assert response.status_code == 404

    def test_delete_nonexistent_sensor_returns_404(self, admin_with_field):
        client, _ = admin_with_field
        response = client.delete("/api/sensors/99999")
        assert response.status_code == 404


class TestSensorsPagination:
    """`/api/sensors/?skip=&limit=` + `/api/sensors/count` — slider pagination."""

    def test_count_empty_db(self, admin_with_field):
        client, _ = admin_with_field
        response = client.get("/api/sensors/count")
        assert response.status_code == 200
        assert response.json() == {"total": 0}

    def test_count_reflects_created_sensors(self, admin_with_field):
        client, field_id = admin_with_field
        for i in range(3):
            client.post("/api/sensors/", json=_sensor_payload(field_id, serial=f"CNT-{i}"))
        response = client.get("/api/sensors/count")
        assert response.json()["total"] == 3

    def test_skip_limit_returns_correct_slice(self, admin_with_field):
        client, field_id = admin_with_field
        ids = []
        for i in range(5):
            created = client.post("/api/sensors/", json=_sensor_payload(field_id, serial=f"SLICE-{i}")).json()
            ids.append(created["id"])

        response = client.get("/api/sensors/?skip=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == ids[2]
        assert data[1]["id"] == ids[3]

    def test_limit_over_max_rejected(self, admin_with_field):
        client, _ = admin_with_field
        response = client.get("/api/sensors/?limit=501")
        assert response.status_code == 422

    def test_negative_skip_rejected(self, admin_with_field):
        client, _ = admin_with_field
        response = client.get("/api/sensors/?skip=-1&limit=10")
        assert response.status_code == 422
