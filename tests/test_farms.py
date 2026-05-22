"""
Farm Read-Only Endpoint Testleri (Cycle 9 prep + REBUILD Faz 1 RBAC).

GET /api/farms/                        — list + region/city/pagination
GET /api/farms/{farm_id}               — detail + nested fields
GET /api/farms/{farm_id}/soil          — soil analyses across farm

REBUILD Faz 1 (`ebbe87f`+) — bu router'ın tüm endpoint'leri artık
Bearer JWT zorunlu + 4-rol RBAC kapsamında:
    farmer    → yalnız kendi çiftlikleri
    developer/overseer/admin → tüm sistem

Mevcut "tüm sistem görünür" varsayımlı testler `admin_client`'a migrate
edildi; RBAC behaviour testleri (`TestFarmerScope`, `TestAnonAccess`,
`TestOverseerReadAll`) yeni eklendi.
"""

from datetime import UTC, datetime

import pytest

from app.models.models import Farm, Field, SoilAnalysis, User


# ───── Fixture: 2 user × 2 çiftlik + 3 tarla + 2 toprak analizi ──────────────
@pytest.fixture
def farm_fixture(db):
    """Marmara'da 1 çiftlik (Test User'a ait), Akdeniz'de 1 çiftlik (aynı User'a)."""
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
    return {
        "fixture_user_id": user.id,
        "marmara_id": f1.id,
        "akdeniz_id": f2.id,
        "field_a_id": field_a.id,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Admin perspektifi — tüm sistem görünümü (mevcut testler buradan migrate edildi)
# ═════════════════════════════════════════════════════════════════════════════


class TestListFarmsAsAdmin:
    """admin tüm fixture çiftliklerini görür."""

    def test_list_empty_returns_only_conftest_default(self, admin_client):
        """Fixture'sız: yalnız `conftest.client` ön-seed default farm görünür."""
        client, _ = admin_client
        r = client.get("/api/farms/")
        assert r.status_code == 200
        body = r.json()
        # conftest.client 1 default farm ekliyor (region="__internal__");
        # fixture'sız test'te admin yalnız bu farm'ı görür.
        assert len(body) == 1
        assert body[0]["region"] == "__internal__"

    def test_list_returns_all_seeded_farms(self, admin_client, farm_fixture):
        client, _ = admin_client
        # 1 conftest default + 2 farm_fixture = 3 toplam (admin perspektifi)
        r = client.get("/api/farms/")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 3
        assert {"id", "user_id", "name", "city", "region", "area_hectares"}.issubset(body[0].keys())

    def test_list_filter_by_region(self, admin_client, farm_fixture):
        client, _ = admin_client
        r = client.get("/api/farms/?region=Marmara")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert body[0]["region"] == "Marmara"

    def test_list_filter_by_city(self, admin_client, farm_fixture):
        client, _ = admin_client
        r = client.get("/api/farms/?city=Antalya")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert body[0]["city"] == "Antalya"

    def test_list_pagination_limit(self, admin_client, farm_fixture):
        client, _ = admin_client
        r = client.get("/api/farms/?limit=1")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_list_skip_overflow_rejected(self, admin_client):
        client, _ = admin_client
        r = client.get("/api/farms/?skip=9999999")
        assert r.status_code == 422


class TestGetFarmDetailAsAdmin:
    def test_detail_returns_farm_with_fields(self, admin_client, farm_fixture):
        client, _ = admin_client
        r = client.get(f"/api/farms/{farm_fixture['marmara_id']}")
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == farm_fixture["marmara_id"]
        assert body["region"] == "Marmara"
        assert len(body["fields"]) == 2

    def test_detail_unknown_id_returns_404(self, admin_client, farm_fixture):
        client, _ = admin_client
        r = client.get("/api/farms/99999")
        assert r.status_code == 404
        assert "bulunamadi" in r.json()["detail"].lower()

    def test_detail_int64_overflow_rejected(self, admin_client):
        client, _ = admin_client
        r = client.get("/api/farms/9223372036854775808")
        assert r.status_code == 422


class TestFarmSoilAnalysesAsAdmin:
    def test_soil_returns_analyses_in_farm(self, admin_client, farm_fixture):
        client, _ = admin_client
        r = client.get(f"/api/farms/{farm_fixture['marmara_id']}/soil")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 2
        dates = [item["analysis_date"] for item in body]
        assert dates == sorted(dates, reverse=True)

    def test_soil_farm_with_no_analyses(self, admin_client, farm_fixture):
        client, _ = admin_client
        r = client.get(f"/api/farms/{farm_fixture['akdeniz_id']}/soil")
        assert r.status_code == 200
        assert r.json() == []

    def test_soil_unknown_farm_returns_404(self, admin_client, farm_fixture):
        client, _ = admin_client
        r = client.get("/api/farms/99999/soil")
        assert r.status_code == 404

    def test_soil_response_shape(self, admin_client, farm_fixture):
        client, _ = admin_client
        r = client.get(f"/api/farms/{farm_fixture['marmara_id']}/soil?limit=1")
        body = r.json()
        assert len(body) == 1
        for k in ("id", "field_id", "analysis_date", "ph_level", "texture_class"):
            assert k in body[0]


# ═════════════════════════════════════════════════════════════════════════════
# RBAC Behaviour — Faz 1 Adım 7 yeni testler
# ═════════════════════════════════════════════════════════════════════════════


class TestAnonAccess:
    """Auth header'sız → tüm farms endpoint'leri 401."""

    def test_list_without_auth_401(self, anon_client):
        r = anon_client.get("/api/farms/")
        assert r.status_code == 401

    def test_detail_without_auth_401(self, anon_client, farm_fixture):
        r = anon_client.get(f"/api/farms/{farm_fixture['marmara_id']}")
        assert r.status_code == 401

    def test_soil_without_auth_401(self, anon_client, farm_fixture):
        r = anon_client.get(f"/api/farms/{farm_fixture['marmara_id']}/soil")
        assert r.status_code == 401


class TestFarmerScope:
    """Farmer yalnız kendi çiftliklerini görür."""

    def test_farmer_list_excludes_other_users_farms(self, farmer_client, farm_fixture):
        """Yeni farmer (farm_fixture user'ından farklı kişi) → kendi listesi boş."""
        client, _ = farmer_client
        r = client.get("/api/farms/")
        assert r.status_code == 200
        # Fixture'daki 2 çiftlik başka user'a ait; farmer kendi 0 çiftliği
        assert r.json() == []

    def test_farmer_detail_others_farm_returns_403(self, farmer_client, farm_fixture):
        """Başkasının çiftliğine erişim → 403."""
        client, _ = farmer_client
        r = client.get(f"/api/farms/{farm_fixture['marmara_id']}")
        assert r.status_code == 403
        assert "yetkin yok" in r.json()["detail"].lower()

    def test_farmer_soil_others_farm_returns_403(self, farmer_client, farm_fixture):
        client, _ = farmer_client
        r = client.get(f"/api/farms/{farm_fixture['marmara_id']}/soil")
        assert r.status_code == 403

    def test_farmer_sees_own_farm_via_seed(self, farmer_client, db):
        """Farmer kendisine ait çiftliği görebilmeli."""
        client, user = farmer_client
        own = Farm(user_id=user.id, name="Benim Çiftliğim", region="Ege", city="İzmir")
        db.add(own)
        db.commit()
        r = client.get("/api/farms/")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert body[0]["name"] == "Benim Çiftliğim"


class TestOverseerAndDeveloperScope:
    """Overseer + developer: read-only sistem-geneli erişim."""

    def test_overseer_sees_all_farms(self, overseer_client, farm_fixture):
        client, _ = overseer_client
        r = client.get("/api/farms/")
        assert r.status_code == 200
        # 1 conftest default + 2 fixture = 3 (overseer tüm sistem read)
        assert len(r.json()) == 3

    def test_overseer_can_get_any_farm_detail(self, overseer_client, farm_fixture):
        client, _ = overseer_client
        r = client.get(f"/api/farms/{farm_fixture['marmara_id']}")
        assert r.status_code == 200
        assert r.json()["region"] == "Marmara"

    def test_developer_sees_all_farms(self, developer_client, farm_fixture):
        client, _ = developer_client
        r = client.get("/api/farms/")
        assert r.status_code == 200
        assert len(r.json()) == 3


# ───── REBUILD Faz 4 — CRUD write testleri ──────────────────────────────
class TestFarmWrite:
    """POST/PATCH/DELETE /api/farms — rol-aware + cascade guard."""

    def test_farmer_creates_own_farm(self, farmer_client):
        client, user = farmer_client
        r = client.post(
            "/api/farms/",
            json={"name": "Yeni Çiftlik", "city": "Konya", "region": "İç Anadolu", "area_hectares": 5.0},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Yeni Çiftlik"
        assert data["user_id"] == user.id  # sahip = current_user

    def test_overseer_cannot_create_403(self, overseer_client):
        client, _ = overseer_client
        r = client.post("/api/farms/", json={"name": "X", "region": "Ege"})
        assert r.status_code == 403

    def test_developer_cannot_create_403(self, developer_client):
        client, _ = developer_client
        r = client.post("/api/farms/", json={"name": "X", "region": "Ege"})
        assert r.status_code == 403

    def test_anon_cannot_create_401(self, anon_client):
        r = anon_client.post("/api/farms/", json={"name": "X", "region": "Ege"})
        assert r.status_code == 401

    def test_farmer_updates_own_farm(self, farmer_client, db):
        client, user = farmer_client
        farm = Farm(user_id=user.id, name="Eski Ad", region="Ege")
        db.add(farm)
        db.commit()
        r = client.patch(f"/api/farms/{farm.id}", json={"name": "Yeni Ad", "area_hectares": 9.0})
        assert r.status_code == 200
        assert r.json()["name"] == "Yeni Ad"
        assert r.json()["area_hectares"] == 9.0

    def test_farmer_cannot_update_others_farm_403(self, farmer_client, db):
        client, _ = farmer_client
        other = Farm(user_id=9999, name="Başka", region="Marmara")
        db.add(other)
        db.commit()
        r = client.patch(f"/api/farms/{other.id}", json={"name": "Hack"})
        assert r.status_code == 403

    def test_delete_farm_without_fields_204(self, farmer_client, db):
        client, user = farmer_client
        farm = Farm(user_id=user.id, name="Boş Çiftlik", region="Ege")
        db.add(farm)
        db.commit()
        fid = farm.id
        r = client.delete(f"/api/farms/{fid}")
        assert r.status_code == 204
        assert db.query(Farm).filter(Farm.id == fid).first() is None

    def test_delete_farm_with_fields_409(self, farmer_client, db):
        client, user = farmer_client
        farm = Farm(user_id=user.id, name="Dolu Çiftlik", region="Ege")
        db.add(farm)
        db.flush()
        db.add(Field(farm_id=farm.id, name="Tarla", soil_type="killi"))
        db.commit()
        r = client.delete(f"/api/farms/{farm.id}")
        assert r.status_code == 409
        assert db.query(Farm).filter(Farm.id == farm.id).first() is not None

    def test_farmer_cannot_delete_others_farm_403(self, farmer_client, db):
        client, _ = farmer_client
        other = Farm(user_id=9999, name="Başka", region="Marmara")
        db.add(other)
        db.commit()
        assert client.delete(f"/api/farms/{other.id}").status_code == 403

    def test_update_missing_farm_404(self, farmer_client):
        client, _ = farmer_client
        assert client.patch("/api/farms/999999", json={"name": "X"}).status_code == 404
