"""
Farm Read-Only Endpoint Testleri (Cycle 9 prep — `app/routers/farms.py`)
========================================================================
GET /api/farms/                        — list + region/city/pagination
GET /api/farms/{farm_id}               — detail + nested fields
GET /api/farms/{farm_id}/soil          — soil analyses across farm
"""

from datetime import UTC, datetime

import pytest

from app.models.models import Farm, Field, SoilAnalysis, User


# ───── Fixture: bir kullanıcı + 2 çiftlik + 3 tarla + 2 toprak analizi ─────
@pytest.fixture
def farm_fixture(db):
    """Marmara'da 1 çiftlik + 2 tarla, Akdeniz'de 1 çiftlik + 1 tarla."""
    user = User(name="Test User", email="farm-fixture@sfdap.test", password_hash="x", role="farmer")
    db.add(user)
    db.flush()

    f1 = Farm(user_id=user.id, name="Marmara Tarlası", city="İstanbul", region="Marmara", area_hectares=12.5)
    f2 = Farm(user_id=user.id, name="Akdeniz Bahçesi", city="Antalya", region="Akdeniz", area_hectares=8.0)
    db.add_all([f1, f2])
    db.flush()

    field_a = Field(farm_id=f1.id, name="Kuzey Tarla", area_hectares=6.0, soil_type="killi")
    field_b = Field(farm_id=f1.id, name="Güney Tarla", area_hectares=6.5, soil_type="tinli")
    field_c = Field(farm_id=f2.id, name="Sera 1", area_hectares=8.0, soil_type="kumlu")
    db.add_all([field_a, field_b, field_c])
    db.flush()

    soil_a = SoilAnalysis(
        field_id=field_a.id,
        analysis_date=datetime(2026, 5, 1, tzinfo=UTC),
        ph_level=6.8,
        organic_matter_pct=3.2,
        nitrogen_mg_kg=45.0,
        texture_class="killi",
    )
    soil_b = SoilAnalysis(
        field_id=field_b.id,
        analysis_date=datetime(2026, 5, 10, tzinfo=UTC),
        ph_level=7.1,
        texture_class="tinli",
    )
    db.add_all([soil_a, soil_b])
    db.commit()
    return {"user_id": user.id, "marmara_id": f1.id, "akdeniz_id": f2.id, "field_a_id": field_a.id}


# ───── GET /api/farms/ ────────────────────────────────────────────────────
class TestListFarms:
    def test_list_empty_returns_200_empty_list(self, client):
        """Boş DB'de liste boş 200 dönmeli."""
        r = client.get("/api/farms/")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_returns_all_seeded_farms(self, client, farm_fixture):
        """Fixture'daki 2 çiftlik liste döner."""
        r = client.get("/api/farms/")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 2
        # FarmResponse alanları
        assert {"id", "user_id", "name", "city", "region", "area_hectares"}.issubset(body[0].keys())

    def test_list_filter_by_region(self, client, farm_fixture):
        """region=Marmara → sadece Marmara çiftliği döner."""
        r = client.get("/api/farms/?region=Marmara")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert body[0]["region"] == "Marmara"

    def test_list_filter_by_city(self, client, farm_fixture):
        """city=Antalya → Akdeniz çiftliği."""
        r = client.get("/api/farms/?city=Antalya")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert body[0]["city"] == "Antalya"

    def test_list_pagination_limit(self, client, farm_fixture):
        """limit=1 → 1 sonuç."""
        r = client.get("/api/farms/?limit=1")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_list_skip_overflow_rejected(self, client):
        """skip > 1_000_000 → 422 (MAX_SKIP guard)."""
        r = client.get("/api/farms/?skip=9999999")
        assert r.status_code == 422


# ───── GET /api/farms/{id} ───────────────────────────────────────────────
class TestGetFarmDetail:
    def test_detail_returns_farm_with_fields(self, client, farm_fixture):
        """Marmara çiftliğinde 2 tarla nested gelir."""
        r = client.get(f"/api/farms/{farm_fixture['marmara_id']}")
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == farm_fixture["marmara_id"]
        assert body["region"] == "Marmara"
        assert len(body["fields"]) == 2
        # FieldSummary alanları
        assert {"id", "name", "area_hectares", "soil_type"}.issubset(body["fields"][0].keys())

    def test_detail_unknown_id_returns_404(self, client, farm_fixture):
        """Olmayan ID → 404 Türkçe detail."""
        r = client.get("/api/farms/99999")
        assert r.status_code == 404
        assert "bulunamadi" in r.json()["detail"].lower()

    def test_detail_int64_overflow_rejected(self, client):
        """farm_id > 2^63-1 → 422 (SqliteSafeInt Path guard)."""
        r = client.get("/api/farms/9223372036854775808")
        assert r.status_code == 422


# ───── GET /api/farms/{id}/soil ──────────────────────────────────────────
class TestFarmSoilAnalyses:
    def test_soil_returns_analyses_in_farm(self, client, farm_fixture):
        """Marmara çiftliğinde 2 toprak analizi (her field için 1)."""
        r = client.get(f"/api/farms/{farm_fixture['marmara_id']}/soil")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 2
        # En yeni önce — analysis_date desc
        dates = [item["analysis_date"] for item in body]
        assert dates == sorted(dates, reverse=True)

    def test_soil_farm_with_no_analyses(self, client, farm_fixture):
        """Akdeniz çiftliği için soil analysis yok — boş liste 200."""
        r = client.get(f"/api/farms/{farm_fixture['akdeniz_id']}/soil")
        assert r.status_code == 200
        assert r.json() == []

    def test_soil_unknown_farm_returns_404(self, client, farm_fixture):
        """Olmayan farm → 404 (boş liste değil)."""
        r = client.get("/api/farms/99999/soil")
        assert r.status_code == 404

    def test_soil_response_shape(self, client, farm_fixture):
        """SoilAnalysisResponse alanlarının tamamı dönmeli."""
        r = client.get(f"/api/farms/{farm_fixture['marmara_id']}/soil?limit=1")
        body = r.json()
        assert len(body) == 1
        item = body[0]
        for k in (
            "id",
            "field_id",
            "analysis_date",
            "ph_level",
            "organic_matter_pct",
            "nitrogen_mg_kg",
            "texture_class",
        ):
            assert k in item
