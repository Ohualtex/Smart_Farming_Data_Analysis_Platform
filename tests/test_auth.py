"""
API Key Authentication Testleri
=================================
API Key doğrulama mekanizması test edilir.
"""

import pytest


# ───── API KEY OLMADAN ERİŞİM ────────────────────────────────────────────────
class TestUnauthorizedAccess:
    def test_post_sensor_without_key_returns_401(self, client):
        """API key olmadan sensör ekleme 401 döndürmeli."""
        # Geçici olarak header'ı kaldır
        original_headers = client.headers.copy()
        client.headers.pop("X-API-Key", None)

        response = client.post("/api/sensors/", json={
            "field_id": 1, "sensor_type": "test", "serial_number": "T-001"
        })
        assert response.status_code == 401

        # Header'ı geri koy
        client.headers.update(original_headers)

    def test_delete_sensor_without_key_returns_401(self, client):
        """API key olmadan sensör silme 401 döndürmeli."""
        original_headers = client.headers.copy()
        client.headers.pop("X-API-Key", None)

        response = client.delete("/api/sensors/1")
        assert response.status_code == 401

        client.headers.update(original_headers)


# ───── YANLIŞ API KEY İLE ERİŞİM ────────────────────────────────────────────
class TestForbiddenAccess:
    def test_post_sensor_with_wrong_key_returns_403(self, client):
        """Yanlış API key ile 403 döndürmeli."""
        response = client.post(
            "/api/sensors/",
            json={"field_id": 1, "sensor_type": "test", "serial_number": "T-002"},
            headers={"X-API-Key": "wrong-key-12345"},
        )
        assert response.status_code == 403

    def test_error_message_turkish(self, client):
        """Hata mesajı Türkçe olmalı."""
        response = client.post(
            "/api/sensors/",
            json={"field_id": 1, "sensor_type": "test", "serial_number": "T-003"},
            headers={"X-API-Key": "wrong-key"},
        )
        assert "gecersiz" in response.json()["detail"].lower()


# ───── DOĞRU API KEY İLE ERİŞİM ─────────────────────────────────────────────
class TestAuthorizedAccess:
    def test_post_sensor_with_valid_key_returns_201(self, client):
        """Doğru API key ile sensör ekleme çalışmalı."""
        response = client.post("/api/sensors/", json={
            "field_id": 1, "sensor_type": "test", "serial_number": "T-004"
        })
        assert response.status_code == 201

    def test_post_weather_with_valid_key_returns_201(self, client):
        """Doğru API key ile hava verisi ekleme çalışmalı."""
        response = client.post("/api/weather/", json={
            "farm_id": 1, "temperature_c": 25.0, "humidity_percent": 55.0
        })
        assert response.status_code == 201


# ───── GET ENDPOINT'LERİ AÇIK KALMALI ───────────────────────────────────────
class TestPublicEndpoints:
    def test_get_sensors_no_key_needed(self, client):
        """GET sensör listesi API key gerektirmemeli."""
        original_headers = client.headers.copy()
        client.headers.pop("X-API-Key", None)

        response = client.get("/api/sensors/")
        assert response.status_code == 200

        client.headers.update(original_headers)

    def test_get_weather_no_key_needed(self, client):
        """GET hava durumu API key gerektirmemeli."""
        original_headers = client.headers.copy()
        client.headers.pop("X-API-Key", None)

        response = client.get("/api/weather/")
        assert response.status_code == 200

        client.headers.update(original_headers)

    def test_health_no_key_needed(self, client):
        """Health check API key gerektirmemeli."""
        original_headers = client.headers.copy()
        client.headers.pop("X-API-Key", None)

        response = client.get("/api/health")
        assert response.status_code == 200

        client.headers.update(original_headers)

    def test_irrigation_predict_no_key_needed(self, client):
        """ML prediction API key gerektirmemeli."""
        original_headers = client.headers.copy()
        client.headers.pop("X-API-Key", None)

        response = client.post("/api/irrigation/predict", json={
            "soil_moisture": 35, "soil_temperature": 22,
            "humidity": 45, "temperature": 28, "precipitation": 0
        })
        assert response.status_code == 200

        client.headers.update(original_headers)
