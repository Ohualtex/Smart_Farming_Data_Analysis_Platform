"""
Hava Durumu Endpoint Testleri
==============================
GET  /api/weather/
POST /api/weather/
GET  /api/weather/latest/{farm_id}
"""

import pytest


SAMPLE_WEATHER = {
    "farm_id": 1,
    "temperature_c": 22.5,
    "humidity_percent": 65.0,
    "precipitation_mm": 0.0,
    "wind_speed_kmh": 12.3,
}


# ───── GET /api/weather/ ──────────────────────────────────────────────────────
class TestGetWeather:
    def test_get_weather_empty_returns_200(self, client):
        """Boş DB'de hava durumu listesi 200 döndürmeli."""
        response = client.get("/api/weather/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_weather_after_create(self, client):
        """Kayıt ekledikten sonra liste dolu gelmeli."""
        client.post("/api/weather/", json=SAMPLE_WEATHER)
        response = client.get("/api/weather/")
        assert len(response.json()) >= 1

    def test_get_weather_farm_id_filter(self, client):
        """farm_id filtresi çalışmalı."""
        # farm_id=1 ekle
        client.post("/api/weather/", json=SAMPLE_WEATHER)
        # farm_id=2 ekle
        other = SAMPLE_WEATHER.copy()
        other["farm_id"] = 2
        client.post("/api/weather/", json=other)

        response = client.get("/api/weather/?farm_id=1")
        results = response.json()
        for item in results:
            assert item["farm_id"] == 1


# ───── POST /api/weather/ ─────────────────────────────────────────────────────
class TestCreateWeather:
    def test_create_weather_returns_201(self, client):
        """Hava durumu kaydı oluşturma 201 döndürmeli."""
        response = client.post("/api/weather/", json=SAMPLE_WEATHER)
        assert response.status_code == 201

    def test_create_weather_response_has_id(self, client):
        """Oluşturulan kaydın id'si olmalı."""
        response = client.post("/api/weather/", json=SAMPLE_WEATHER)
        assert "id" in response.json()

    def test_create_weather_temperature_stored(self, client):
        """Sıcaklık değeri doğru saklanmalı."""
        response = client.post("/api/weather/", json=SAMPLE_WEATHER)
        assert response.json()["temperature_c"] == SAMPLE_WEATHER["temperature_c"]

    def test_create_weather_missing_farm_id_returns_422(self, client):
        """farm_id eksikse 422 döndürmeli."""
        invalid = {"temperature": 22.5, "humidity": 65.0}
        response = client.post("/api/weather/", json=invalid)
        assert response.status_code == 422


# ───── GET /api/weather/latest/{farm_id} ─────────────────────────────────────
class TestGetLatestWeather:
    def test_latest_weather_existing_farm(self, client):
        """Var olan farm için en son kayıt dönmeli."""
        client.post("/api/weather/", json=SAMPLE_WEATHER)
        response = client.get(f"/api/weather/latest/{SAMPLE_WEATHER['farm_id']}")
        assert response.status_code == 200
        assert response.json()["farm_id"] == SAMPLE_WEATHER["farm_id"]

    def test_latest_weather_nonexistent_farm_returns_404(self, client):
        """Kayıt olmayan farm için 404 döndürmeli."""
        response = client.get("/api/weather/latest/99999")
        assert response.status_code == 404
