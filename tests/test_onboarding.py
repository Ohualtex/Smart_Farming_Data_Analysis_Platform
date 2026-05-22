"""
Onboarding Endpoint Tests — REBUILD Faz 6
===========================================
`POST /api/onboarding/demo` — boş hesaba tek-tık demo veri kurulumu.

Kapsama matriksi:
    farmer (boş)      → 201, çiftlik + 2 tarla + sensör/okuma + uyarı
    farmer (dolu)     → 409 (mevcut veri korunur)
    overseer/developer→ 403 (read-only)
    anon              → 401
"""

from __future__ import annotations

from app.models.models import Farm, Field, SoilMoistureReading, SystemAlert


class TestOnboardingDemo:
    def test_empty_farmer_gets_demo_data(self, farmer_client, db):
        client, user = farmer_client
        resp = client.post("/api/onboarding/demo")
        assert resp.status_code == 201
        data = resp.json()
        assert data["fields_created"] == 2
        assert data["first_field_id"] is not None
        # DB'de gerçekten kuruldu mu?
        farms = db.query(Farm).filter(Farm.user_id == user.id).all()
        assert len(farms) == 1
        fields = db.query(Field).filter(Field.farm_id == farms[0].id).all()
        assert len(fields) == 2
        # Susuz tarla için kritik uyarı üretildi
        alerts = db.query(SystemAlert).filter(SystemAlert.farm_id == farms[0].id).all()
        assert any(a.severity == "critical" for a in alerts)
        # Okumalar var
        assert db.query(SoilMoistureReading).count() > 0

    def test_demo_then_dashboard_reflects(self, farmer_client):
        client, _user = farmer_client
        client.post("/api/onboarding/demo")
        summary = client.get("/api/dashboard/summary").json()
        assert summary["farm_count"] == 1
        assert summary["field_count"] == 2

    def test_farmer_with_farm_gets_409(self, farmer_client, db):
        client, user = farmer_client
        db.add(Farm(user_id=user.id, name="Var olan", region="Ege"))
        db.commit()
        resp = client.post("/api/onboarding/demo")
        assert resp.status_code == 409

    def test_demo_idempotent_second_call_409(self, farmer_client):
        client, _user = farmer_client
        assert client.post("/api/onboarding/demo").status_code == 201
        assert client.post("/api/onboarding/demo").status_code == 409

    def test_overseer_forbidden_403(self, overseer_client):
        client, _ = overseer_client
        assert client.post("/api/onboarding/demo").status_code == 403

    def test_developer_forbidden_403(self, developer_client):
        client, _ = developer_client
        assert client.post("/api/onboarding/demo").status_code == 403

    def test_anon_401(self, anon_client):
        assert anon_client.post("/api/onboarding/demo").status_code == 401

    def test_admin_can_load_demo(self, admin_client):
        # admin_client ayrı bir admin user (kendi çiftliği yok) → write set'inde
        # olduğundan kendi adına demo kurabilir (201).
        client, _admin = admin_client
        assert client.post("/api/onboarding/demo").status_code == 201
