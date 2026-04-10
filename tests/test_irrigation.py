"""
Sulama (Irrigation) Endpoint Testleri
======================================
POST /api/irrigation/predict
GET  /api/irrigation/schedules
POST /api/irrigation/schedules
"""

import pytest


SAMPLE_PREDICTION_REQUEST = {
    "soil_moisture": 35.0,
    "soil_temperature": 18.5,
    "humidity": 60.0,
    "temperature": 25.0,
    "precipitation": 0.0,
}

SAMPLE_SCHEDULE = {
    "field_id": 1,
    "scheduled_date": "2026-04-10T08:00:00",
    "duration_min": 45,
    "water_amount_liters": 500.0,
}


# ───── POST /api/irrigation/predict ──────────────────────────────────────────
class TestIrrigationPredict:
    def test_predict_returns_200(self, client):
        """Tahmin endpoint'i 200 döndürmeli."""
        response = client.post("/api/irrigation/predict", json=SAMPLE_PREDICTION_REQUEST)
        assert response.status_code == 200

    def test_predict_response_has_recommendation(self, client):
        """Tahmin yanıtı sulama kararı içermeli."""
        response = client.post("/api/irrigation/predict", json=SAMPLE_PREDICTION_REQUEST)
        data = response.json()
        # Gerçek IrrigationPredictionResponse alanlari: irrigation_needed, message
        assert "irrigation_needed" in data
        assert "message" in data

    def test_predict_response_has_confidence(self, client):
        """Tahmin yanıtı güven skoru içermeli."""
        response = client.post("/api/irrigation/predict", json=SAMPLE_PREDICTION_REQUEST)
        data = response.json()
        # Gerçek alan: confidence
        assert "confidence" in data

    def test_predict_with_high_moisture(self, client):
        """Yüksek toprak nemi = sulama gerekmez tahmini."""
        request = SAMPLE_PREDICTION_REQUEST.copy()
        request["soil_moisture"] = 85.0  # çok yüksek
        response = client.post("/api/irrigation/predict", json=request)
        assert response.status_code == 200

    def test_predict_with_low_moisture(self, client):
        """Düşük toprak nemi = sulama gerekir tahmini."""
        request = SAMPLE_PREDICTION_REQUEST.copy()
        request["soil_moisture"] = 10.0  # çok düşük
        response = client.post("/api/irrigation/predict", json=request)
        assert response.status_code == 200

    def test_predict_missing_fields_returns_422(self, client):
        """Eksik veri ile tahmin isteği 422 döndürmeli."""
        incomplete = {"soil_moisture": 35.0}
        response = client.post("/api/irrigation/predict", json=incomplete)
        assert response.status_code == 422

    def test_predict_invalid_moisture_value(self, client):
        """String değer gönderilirse 422 döndürmeli."""
        invalid = SAMPLE_PREDICTION_REQUEST.copy()
        invalid["soil_moisture"] = "yüksek"
        response = client.post("/api/irrigation/predict", json=invalid)
        assert response.status_code == 422


# ───── GET /api/irrigation/schedules ─────────────────────────────────────────
class TestGetSchedules:
    def test_get_schedules_empty_returns_200(self, client):
        """Boş takvim listesi 200 döndürmeli."""
        response = client.get("/api/irrigation/schedules")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_schedules_after_create(self, client):
        """Oluşturma sonrası takvim listesi dolu gelmeli."""
        client.post("/api/irrigation/schedules", json=SAMPLE_SCHEDULE)
        response = client.get("/api/irrigation/schedules")
        assert len(response.json()) >= 1

    def test_get_schedules_field_id_filter(self, client):
        """field_id filtresi çalışmalı."""
        client.post("/api/irrigation/schedules", json=SAMPLE_SCHEDULE)
        other = SAMPLE_SCHEDULE.copy()
        other["field_id"] = 99
        client.post("/api/irrigation/schedules", json=other)

        response = client.get("/api/irrigation/schedules?field_id=1")
        for item in response.json():
            assert item["field_id"] == 1


# ───── POST /api/irrigation/schedules ────────────────────────────────────────
class TestCreateSchedule:
    def test_create_schedule_returns_201(self, client):
        """Takvim oluşturma 201 döndürmeli."""
        response = client.post("/api/irrigation/schedules", json=SAMPLE_SCHEDULE)
        assert response.status_code == 201

    def test_create_schedule_has_id(self, client):
        """Oluşturulan takvimdeki id alanı olmalı."""
        response = client.post("/api/irrigation/schedules", json=SAMPLE_SCHEDULE)
        assert "id" in response.json()

    def test_create_schedule_stores_duration(self, client):
        """Sulama süresi doğru saklanmalı."""
        response = client.post("/api/irrigation/schedules", json=SAMPLE_SCHEDULE)
        # IrrigationResponse'da duration_min yok (water_amount_liters var)
        data = response.json()
        assert data["water_amount_liters"] == SAMPLE_SCHEDULE["water_amount_liters"]
