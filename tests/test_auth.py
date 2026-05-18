"""
Auth & Public Endpoint Erişim Testleri — REBUILD Faz 1 RBAC paradigm.

Eski `test_auth.py` (X-API-Key tabanlı) bu RBAC pivot'unda yeniden yazıldı.
Artık asıl auth mekanizması Bearer JWT + 4-rol RBAC; ayrıntılı behaviour
testleri için `test_auth_backend.py` (JWT lifecycle) ve `test_farms.py`
(rol bazlı scope) referans.

Bu dosyada kalan kapsam: hangi endpoint'lerin **anonim erişime açık**
olduğunu ve hangi temel write akışlarının **admin Bearer ile** çalıştığını
sabitler.
"""

from __future__ import annotations

import pytest

from app.models.models import Farm, Field


@pytest.fixture
def admin_with_field(admin_client, db):
    """admin + 1 farm + 1 field — sensors/weather/irrigation POST testleri için."""
    client, user = admin_client
    farm = Farm(user_id=user.id, name="Auth Test Farm", region="Marmara", city="İstanbul")
    db.add(farm)
    db.flush()
    field = Field(farm_id=farm.id, name="Auth Test Field", soil_type="killi")
    db.add(field)
    db.commit()
    return client, farm.id, field.id


# ───── Bearer JWT olmadan erişim — sensors/farms write 401 ─────────────────────
class TestUnauthenticatedWriteBlocked:
    def test_anon_post_sensor_returns_401(self, anon_client):
        """Bearer yok → sensors POST 401."""
        response = anon_client.post(
            "/api/sensors/",
            json={"field_id": 1, "sensor_type": "test", "serial_number": "T-001"},
        )
        assert response.status_code == 401

    def test_anon_delete_sensor_returns_401(self, anon_client):
        """Bearer yok → sensors DELETE 401."""
        response = anon_client.delete("/api/sensors/1")
        assert response.status_code == 401


# ───── Admin Bearer ile write OK ─────────────────────────────────────────────
class TestAdminWriteAuthorized:
    def test_admin_post_sensor_returns_201(self, admin_with_field):
        client, _, field_id = admin_with_field
        response = client.post(
            "/api/sensors/",
            json={"field_id": field_id, "sensor_type": "test", "serial_number": "T-004"},
        )
        assert response.status_code == 201

    def test_admin_post_weather_returns_201(self, admin_with_field):
        client, farm_id, _ = admin_with_field
        response = client.post(
            "/api/weather/",
            json={"farm_id": farm_id, "temperature_c": 25.0, "humidity_percent": 55.0},
        )
        assert response.status_code == 201


# ───── Anon erişimine kalan public endpoint'ler ──────────────────────────────
class TestStillPublicEndpoints:
    """Bearer olmadan erişilebilir kalan endpoint'ler.

    REBUILD Faz 1 sonrası `farms`/`sensors`/`alerts`/`analytics`/`weather`
    GET'leri auth ister; sadece health probe + ML prediction stateless
    endpoint'leri Bearer'sız erişilebilir.
    """

    def test_health_no_auth_needed(self, anon_client):
        response = anon_client.get("/api/health")
        assert response.status_code == 200

    def test_irrigation_predict_no_auth_needed(self, anon_client):
        """ML predict stateless — DB'ye yazmaz, public kalır (Faz 1 sonu)."""
        response = anon_client.post(
            "/api/irrigation/predict",
            json={
                "soil_moisture": 35,
                "soil_temperature": 22,
                "humidity": 45,
                "temperature": 28,
                "precipitation": 0,
            },
        )
        assert response.status_code == 200
