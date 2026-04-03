"""
Sensör Endpoint Testleri
========================
GET  /api/sensors/
POST /api/sensors/
GET  /api/sensors/{id}
DELETE /api/sensors/{id}
POST /api/sensors/readings
GET  /api/sensors/{id}/readings
"""

import pytest


# ───── Yardımcı veri ─────────────────────────────────────────────────────────
SAMPLE_SENSOR = {
    "serial_number": "SENSOR-001",
    "sensor_type": "soil_moisture",
    "lat": 38.7225,
    "lng": 39.4900,
    "field_id": 1,
}


# ───── GET /api/sensors/ ──────────────────────────────────────────────────────
class TestGetSensors:
    def test_get_sensors_empty_returns_200(self, client):
        """Boş DB'de sensör listesi 200 ve boş liste döndürmeli."""
        response = client.get("/api/sensors/")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_sensors_returns_list(self, client):
        """Sensör eklendikten sonra liste dolu gelmeli."""
        client.post("/api/sensors/", json=SAMPLE_SENSOR)
        response = client.get("/api/sensors/")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_get_sensors_with_limit(self, client):
        """limit parametresi çalışmalı."""
        for i in range(3):
            sensor = SAMPLE_SENSOR.copy()
            sensor["serial_number"] = f"SENSOR-00{i}"
            client.post("/api/sensors/", json=sensor)
        response = client.get("/api/sensors/?limit=2")
        assert len(response.json()) <= 2


# ───── POST /api/sensors/ ─────────────────────────────────────────────────────
class TestCreateSensor:
    def test_create_sensor_returns_201(self, client):
        """Yeni sensör oluşturma 201 döndürmeli."""
        response = client.post("/api/sensors/", json=SAMPLE_SENSOR)
        assert response.status_code == 201

    def test_create_sensor_response_has_id(self, client):
        """Oluşturulan sensörün id'si olmalı."""
        response = client.post("/api/sensors/", json=SAMPLE_SENSOR)
        data = response.json()
        assert "id" in data
        assert data["id"] is not None

    def test_create_sensor_data_matches(self, client):
        """Oluşturulan sensörün verileri gönderilen verilerle eşleşmeli."""
        response = client.post("/api/sensors/", json=SAMPLE_SENSOR)
        data = response.json()
        assert data["serial_number"] == SAMPLE_SENSOR["serial_number"]
        assert data["sensor_type"] == SAMPLE_SENSOR["sensor_type"]

    def test_create_sensor_missing_field_returns_422(self, client):
        """Zorunlu alan eksikse 422 döndürmeli."""
        invalid = {"sensor_type": "soil_moisture"}  # serial_number ve field_id eksik
        response = client.post("/api/sensors/", json=invalid)
        assert response.status_code == 422


# ───── GET /api/sensors/{id} ──────────────────────────────────────────────────
class TestGetSensorById:
    def test_get_existing_sensor(self, client):
        """Var olan sensörü ID ile getirme çalışmalı."""
        created = client.post("/api/sensors/", json=SAMPLE_SENSOR).json()
        response = client.get(f"/api/sensors/{created['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_get_nonexistent_sensor_returns_404(self, client):
        """Olmayan sensör için 404 döndürmeli."""
        response = client.get("/api/sensors/99999")
        assert response.status_code == 404

    def test_get_sensor_404_message(self, client):
        """404 mesajı Türkçe olmalı."""
        response = client.get("/api/sensors/99999")
        assert "bulunamadi" in response.json()["detail"].lower()


# ───── DELETE /api/sensors/{id} ───────────────────────────────────────────────
class TestDeleteSensor:
    def test_delete_existing_sensor(self, client):
        """Var olan sensör silinebilmeli."""
        created = client.post("/api/sensors/", json=SAMPLE_SENSOR).json()
        response = client.delete(f"/api/sensors/{created['id']}")
        assert response.status_code == 200

    def test_delete_removes_sensor(self, client):
        """Silinen sensör artık getirilemez olmalı."""
        created = client.post("/api/sensors/", json=SAMPLE_SENSOR).json()
        client.delete(f"/api/sensors/{created['id']}")
        response = client.get(f"/api/sensors/{created['id']}")
        assert response.status_code == 404

    def test_delete_nonexistent_sensor_returns_404(self, client):
        """Olmayan sensörü silmeye çalışmak 404 döndürmeli."""
        response = client.delete("/api/sensors/99999")
        assert response.status_code == 404
