"""
Gübreleme Servisi Testleri
============================
fertilizer_service ve /api/fertilizer endpoint testleri.

Ayşe Eslem Çekici — Cycle 5 Görevi
"""

from app.services.fertilizer_service import FertilizerService

# ─── SERVİS UNIT TESTLERİ ───────────────────────────────────────


class TestFertilizerServiceRecommend:
    """NPK hesaplama doğruluğu testleri."""

    def setup_method(self):
        self.service = FertilizerService()

    def test_recommend_wheat_with_deficit(self):
        result = self.service.recommend(
            crop_type="wheat",
            soil_nitrogen=50.0,
            soil_phosphorus=20.0,
            soil_potassium=10.0,
            area_hectares=2.0,
        )
        assert result["crop_type"] == "wheat"
        assert result["nitrogen_needed_kg"] > 0
        assert result["phosphorus_needed_kg"] > 0
        assert result["potassium_needed_kg"] > 0
        assert result["total_fertilizer_kg"] > 0

    def test_recommend_sufficient_soil(self):
        """Toprak yeterli olduğunda gübre gerekmez."""
        result = self.service.recommend(
            crop_type="wheat",
            soil_nitrogen=200.0,
            soil_phosphorus=200.0,
            soil_potassium=200.0,
            area_hectares=1.0,
        )
        assert result["nitrogen_needed_kg"] == 0
        assert result["phosphorus_needed_kg"] == 0
        assert result["potassium_needed_kg"] == 0
        assert result["total_fertilizer_kg"] == 0
        assert "gerekmez" in result["recommendation"].lower() or "yeterli" in result["recommendation"].lower()

    def test_recommend_unknown_crop_returns_error(self):
        result = self.service.recommend(
            crop_type="mango",
            soil_nitrogen=50.0,
            soil_phosphorus=20.0,
            soil_potassium=10.0,
            area_hectares=1.0,
        )
        assert result.get("error") is True
        assert "Bilinmeyen" in result["message"]

    def test_recommend_case_insensitive(self):
        result = self.service.recommend(
            crop_type="WHEAT",
            soil_nitrogen=50.0,
            soil_phosphorus=20.0,
            soil_potassium=10.0,
            area_hectares=1.0,
        )
        assert result["crop_type"] == "wheat"

    def test_recommend_all_crops_valid(self):
        for crop in self.service.CROP_NPK_REQUIREMENTS:
            result = self.service.recommend(
                crop_type=crop,
                soil_nitrogen=0.0,
                soil_phosphorus=0.0,
                soil_potassium=0.0,
                area_hectares=1.0,
            )
            assert "crop_type" in result
            assert result["total_fertilizer_kg"] > 0

    def test_recommend_returns_turkish_name(self):
        result = self.service.recommend(
            crop_type="tomato",
            soil_nitrogen=50.0,
            soil_phosphorus=50.0,
            soil_potassium=50.0,
            area_hectares=1.0,
        )
        assert result["crop_name_tr"] == "Domates"


class TestFertilizerServiceSchedule:
    """Gübreleme takvimi testleri."""

    def setup_method(self):
        self.service = FertilizerService()

    def test_schedule_returns_5_phases(self):
        schedule = self.service.generate_schedule(
            crop_type="corn",
            planting_date="2026-05-01",
            area_hectares=3.0,
        )
        assert len(schedule) == 5

    def test_schedule_has_required_fields(self):
        schedule = self.service.generate_schedule(
            crop_type="wheat",
            planting_date="2026-03-15",
            area_hectares=1.0,
        )
        for item in schedule:
            assert "phase" in item
            assert "timing" in item
            assert "target_date" in item
            assert "fertilizer_type" in item
            assert "amount_kg_per_hectare" in item

    def test_schedule_unknown_crop_returns_empty(self):
        schedule = self.service.generate_schedule(
            crop_type="banana",
            planting_date="2026-05-01",
            area_hectares=1.0,
        )
        assert schedule == []

    def test_schedule_dates_are_sequential(self):
        schedule = self.service.generate_schedule(
            crop_type="tomato",
            planting_date="2026-04-15",
            area_hectares=2.0,
        )
        # İlk tarih (toprak hazırlığı) ekim öncesi olmalı
        assert schedule[0]["target_date"] < schedule[1]["target_date"]


class TestSupportedCrops:
    """Desteklenen bitki türleri testi."""

    def setup_method(self):
        self.service = FertilizerService()

    def test_returns_all_crops(self):
        crops = self.service.get_supported_crops()
        # Cycle 6: 8 → 17 (Türkiye'nin 7 bölgesi için bitki yelpazesi genişletildi)
        assert len(crops) == 17

    def test_crop_has_required_fields(self):
        crops = self.service.get_supported_crops()
        for crop in crops:
            assert "crop_type" in crop
            assert "name_tr" in crop
            assert "nitrogen_need" in crop


# ─── API ENDPOINT TESTLERİ ──────────────────────────────────────


class TestFertilizerRecommendEndpoint:
    """POST /api/fertilizer/recommend testleri."""

    def test_recommend_returns_200(self, client):
        response = client.post(
            "/api/fertilizer/recommend",
            json={
                "crop_type": "wheat",
                "soil_nitrogen": 50.0,
                "soil_phosphorus": 30.0,
                "soil_potassium": 20.0,
                "area_hectares": 1.0,
            },
        )
        assert response.status_code == 200

    def test_recommend_response_has_npk(self, client):
        response = client.post(
            "/api/fertilizer/recommend",
            json={
                "crop_type": "tomato",
                "soil_nitrogen": 40.0,
                "soil_phosphorus": 20.0,
                "soil_potassium": 50.0,
                "area_hectares": 2.0,
            },
        )
        data = response.json()
        assert "nitrogen_needed_kg" in data
        assert "phosphorus_needed_kg" in data
        assert "potassium_needed_kg" in data
        assert "recommendation" in data

    def test_recommend_unknown_crop_returns_400(self, client):
        response = client.post(
            "/api/fertilizer/recommend",
            json={
                "crop_type": "mango",
                "soil_nitrogen": 50.0,
                "soil_phosphorus": 30.0,
                "soil_potassium": 20.0,
                "area_hectares": 1.0,
            },
        )
        assert response.status_code == 400

    def test_recommend_missing_field_returns_422(self, client):
        response = client.post(
            "/api/fertilizer/recommend",
            json={"crop_type": "wheat"},
        )
        assert response.status_code == 422


class TestFertilizerScheduleEndpoint:
    """POST /api/fertilizer/schedules testleri."""

    def test_schedule_returns_200(self, client):
        response = client.post(
            "/api/fertilizer/schedules",
            json={
                "crop_type": "corn",
                "planting_date": "2026-05-01",
                "area_hectares": 3.0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    def test_schedule_unknown_crop_returns_400(self, client):
        response = client.post(
            "/api/fertilizer/schedules",
            json={
                "crop_type": "banana",
                "planting_date": "2026-05-01",
                "area_hectares": 1.0,
            },
        )
        assert response.status_code == 400


class TestFertilizerCropsEndpoint:
    """GET /api/fertilizer/crops testleri."""

    def test_crops_returns_200(self, client):
        response = client.get("/api/fertilizer/crops")
        assert response.status_code == 200

    def test_crops_returns_list(self, client):
        response = client.get("/api/fertilizer/crops")
        data = response.json()
        assert "crops" in data
        # Cycle 6: 8 → 17 bitki türü
        assert data["count"] == 17
