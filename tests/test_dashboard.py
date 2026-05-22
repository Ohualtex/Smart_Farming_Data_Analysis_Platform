"""
Dashboard Endpoint Tests — REBUILD Faz 2
==========================================
`GET /api/dashboard/summary` rol-aware tek-ekran özet.

Kapsama matriksi:
    anon       → 401
    farmer     → scope='user', kendi farm zinciri (system-wide alert dışlanır)
    farmer (boş hesap) → tüm sayımlar 0, status='no_data'
    developer  → scope='system', sistem-geneli sayım
    overseer   → scope='system', sistem-geneli sayım
    admin      → scope='system', sistem-geneli sayım
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models.models import (
    Farm,
    Field,
    IrrigationSchedule,
    PlantHealthImage,
    Sensor,
    SoilMoistureReading,
    SystemAlert,
)

# ─── Yardımcı seed helper'ları ────────────────────────────────


def _seed_farmer_chain(db, user_id: int, moisture_avg: float = 25.0):
    """Farmer'a ait Farm → Field → Sensor → Reading zinciri kur.

    `moisture_avg` ile son 1 saatlik tek okumanın değeri kontrol edilebilir
    (status='dry'/'optimal'/'wet' assert'leri için).
    """
    farm = Farm(user_id=user_id, name="Ahmet Çiftliği", region="İç Anadolu", city="Konya")
    db.add(farm)
    db.flush()
    field = Field(farm_id=farm.id, name="Tarla A", soil_type="killi", area_hectares=2.5)
    db.add(field)
    db.flush()
    sensor = Sensor(field_id=field.id, sensor_type="soil_moisture", serial_number=f"SN-{user_id}-001")
    db.add(sensor)
    db.flush()
    db.add(
        SoilMoistureReading(
            sensor_id=sensor.id,
            moisture_percent=moisture_avg,
            reading_timestamp=datetime.now(UTC) - timedelta(hours=1),
        )
    )
    db.commit()
    return farm, field, sensor


# ─── Anonim erişim ─────────────────────────────────────────────


class TestDashboardAnonAccess:
    def test_anon_summary_returns_401(self, anon_client):
        resp = anon_client.get("/api/dashboard/summary")
        assert resp.status_code == 401


# ─── Farmer scope ──────────────────────────────────────────────


class TestDashboardFarmerScope:
    def test_empty_farmer_returns_zeros_and_no_data(self, farmer_client):
        client, _user = farmer_client
        resp = client.get("/api/dashboard/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["scope"] == "user"
        assert data["user_role"] == "farmer"
        assert data["farm_count"] == 0
        assert data["field_count"] == 0
        assert data["sensor_count"] == 0
        assert data["soil_moisture_today"]["status"] == "no_data"
        assert data["soil_moisture_today"]["avg_moisture_percent"] is None
        assert data["last_irrigation"]["irrigation_id"] is None
        assert data["open_alerts"]["total"] == 0
        assert data["last_disease"]["image_id"] is None

    def test_farmer_sees_own_farm_chain_only(self, farmer_client, db):
        client, user = farmer_client
        _seed_farmer_chain(db, user.id, moisture_avg=25.0)
        # Başka bir farmer'ın chain'i — sızmasın
        other_user_id = 9999
        # NOT: gerçek bir User satırı olmasa da Farm.user_id'yi
        # FK constraint dışı ID ile set ediyoruz (SQLite test'te FK
        # enforce default kapalı); test DB'sinde FK violation atmaz.
        other_farm = Farm(user_id=other_user_id, name="Başka Çiftlik", region="Marmara")
        db.add(other_farm)
        db.commit()

        resp = client.get("/api/dashboard/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["farm_count"] == 1
        assert data["field_count"] == 1
        assert data["sensor_count"] == 1
        assert data["soil_moisture_today"]["status"] == "dry"  # 25 < 30
        assert data["soil_moisture_today"]["avg_moisture_percent"] == 25.0
        assert data["soil_moisture_today"]["reading_count"] == 1
        assert data["soil_moisture_today"]["sensor_count"] == 1

    def test_moisture_status_optimal_band(self, farmer_client, db):
        client, user = farmer_client
        _seed_farmer_chain(db, user.id, moisture_avg=50.0)
        resp = client.get("/api/dashboard/summary")
        assert resp.json()["soil_moisture_today"]["status"] == "optimal"

    def test_moisture_status_wet_band(self, farmer_client, db):
        client, user = farmer_client
        _seed_farmer_chain(db, user.id, moisture_avg=85.0)
        resp = client.get("/api/dashboard/summary")
        assert resp.json()["soil_moisture_today"]["status"] == "wet"

    def test_farmer_excludes_system_wide_alert(self, farmer_client, db):
        """farm_id=None olan sistem-wide alert farmer'a görünmemeli."""
        client, user = farmer_client
        farm, _field, _sensor = _seed_farmer_chain(db, user.id)
        # Kendi farm'ına bağlı alert (görünmeli)
        db.add(
            SystemAlert(
                farm_id=farm.id,
                alert_type="sensor_anomaly",
                severity="critical",
                message="Sensör arıza",
                is_resolved=False,
            )
        )
        # System-wide alert (farm_id=None) — farmer'a yansımamalı
        db.add(
            SystemAlert(
                farm_id=None,
                alert_type="system_error",
                severity="medium",
                message="Sistem uyarısı",
                is_resolved=False,
            )
        )
        # Başka farmer'ın alert'i (görünmemeli)
        other_farm = Farm(user_id=42, name="Başka", region="Karadeniz")
        db.add(other_farm)
        db.flush()
        db.add(
            SystemAlert(
                farm_id=other_farm.id,
                alert_type="sensor_anomaly",
                severity="low",
                message="Başka çiftlik",
                is_resolved=False,
            )
        )
        db.commit()
        resp = client.get("/api/dashboard/summary")
        data = resp.json()
        assert data["open_alerts"]["total"] == 1
        assert data["open_alerts"]["by_severity"]["critical"] == 1
        assert data["open_alerts"]["by_severity"]["medium"] == 0
        assert data["open_alerts"]["by_severity"]["low"] == 0
        assert data["open_alerts"]["latest_severity"] == "critical"

    def test_farmer_resolved_alerts_not_counted(self, farmer_client, db):
        client, user = farmer_client
        farm, _field, _sensor = _seed_farmer_chain(db, user.id)
        db.add(
            SystemAlert(
                farm_id=farm.id,
                alert_type="sensor_anomaly",
                severity="critical",
                message="Çözüldü zaten",
                is_resolved=True,
            )
        )
        db.commit()
        data = client.get("/api/dashboard/summary").json()
        assert data["open_alerts"]["total"] == 0

    def test_farmer_last_irrigation_uses_latest(self, farmer_client, db):
        client, user = farmer_client
        farm, field, _sensor = _seed_farmer_chain(db, user.id)
        # 3 sulama kaydı — en yenisi gelmeli
        db.add(
            IrrigationSchedule(
                field_id=field.id,
                scheduled_date=datetime.now(UTC) - timedelta(days=5),
                water_amount_liters=100.0,
                status="completed",
            )
        )
        db.add(
            IrrigationSchedule(
                field_id=field.id,
                scheduled_date=datetime.now(UTC) - timedelta(days=1),
                water_amount_liters=250.0,
                status="completed",
            )
        )
        db.add(
            IrrigationSchedule(
                field_id=field.id,
                scheduled_date=datetime.now(UTC) - timedelta(days=3),
                water_amount_liters=180.0,
                status="completed",
            )
        )
        db.commit()
        data = client.get("/api/dashboard/summary").json()
        assert data["last_irrigation"]["water_amount_liters"] == 250.0
        assert data["last_irrigation"]["field_name"] == "Tarla A"
        assert data["last_irrigation"]["status"] == "completed"

    def test_farmer_last_disease_returns_latest_diagnosis(self, farmer_client, db):
        client, user = farmer_client
        _farm, field, _sensor = _seed_farmer_chain(db, user.id)
        # diagnosis=None olan eski kayıt sayılmamalı
        db.add(PlantHealthImage(field_id=field.id, image_url="old.jpg", diagnosis=None))
        db.add(
            PlantHealthImage(
                field_id=field.id,
                image_url="latest.jpg",
                captured_at=datetime.now(UTC) - timedelta(hours=2),
                diagnosis="leaf_rust",
                confidence_score=0.87,
                severity="moderate",
            )
        )
        db.commit()
        data = client.get("/api/dashboard/summary").json()
        assert data["last_disease"]["diagnosis"] == "leaf_rust"
        assert data["last_disease"]["severity"] == "moderate"
        assert data["last_disease"]["confidence_score"] == 0.87
        assert data["last_disease"]["field_name"] == "Tarla A"

    def test_farmer_old_reading_outside_24h_excluded(self, farmer_client, db):
        """26 saat önceki okuma 'bugün' penceresi dışı → no_data."""
        client, user = farmer_client
        farm, field, sensor = _seed_farmer_chain(db, user.id, moisture_avg=25.0)
        # 1 saat önceki seed reading'i SİL, yerine 26 saat önceki ekle
        db.query(SoilMoistureReading).delete()
        db.add(
            SoilMoistureReading(
                sensor_id=sensor.id,
                moisture_percent=40.0,
                reading_timestamp=datetime.now(UTC) - timedelta(hours=26),
            )
        )
        db.commit()
        data = client.get("/api/dashboard/summary").json()
        assert data["soil_moisture_today"]["status"] == "no_data"
        assert data["soil_moisture_today"]["reading_count"] == 0


# ─── System scope (admin/overseer/developer) ──────────────────


class TestDashboardSystemScope:
    def test_admin_scope_is_system(self, admin_client):
        client, _user = admin_client
        data = client.get("/api/dashboard/summary").json()
        assert data["scope"] == "system"
        assert data["user_role"] == "admin"

    def test_developer_scope_is_system(self, developer_client):
        client, _user = developer_client
        data = client.get("/api/dashboard/summary").json()
        assert data["scope"] == "system"
        assert data["user_role"] == "developer"

    def test_overseer_scope_is_system(self, overseer_client):
        client, _user = overseer_client
        data = client.get("/api/dashboard/summary").json()
        assert data["scope"] == "system"
        assert data["user_role"] == "overseer"

    def test_admin_sees_all_farms_including_other_users(self, admin_client, db):
        client, _user = admin_client
        # Başka kullanıcıya ait farm — admin görmeli
        db.add(Farm(user_id=99, name="Başka Çiftlik", region="Marmara"))
        db.commit()
        data = client.get("/api/dashboard/summary").json()
        # conftest'in ön-seed farm'ı (1) + bu yeni farm = 2; admin scope
        # ayrıca admin_client'ın kendi ön-seed bypass user'ı yarattığı için
        # toplam ≥ 2 olduğunu doğrula.
        assert data["farm_count"] >= 2

    def test_admin_includes_system_wide_alerts(self, admin_client, db):
        client, _user = admin_client
        db.add(
            SystemAlert(
                farm_id=None,
                alert_type="system_error",
                severity="critical",
                message="Sistem-wide",
                is_resolved=False,
            )
        )
        db.commit()
        data = client.get("/api/dashboard/summary").json()
        assert data["open_alerts"]["total"] >= 1
        assert data["open_alerts"]["by_severity"]["critical"] >= 1


# ─── Response shape kontratı ──────────────────────────────────


class TestDashboardResponseShape:
    def test_response_carries_generated_at(self, farmer_client):
        client, _user = farmer_client
        data = client.get("/api/dashboard/summary").json()
        # ISO 8601 + UTC suffix (UtcDateTime serializer)
        assert "generated_at" in data
        assert data["generated_at"].endswith("+00:00") or data["generated_at"].endswith("Z")

    def test_response_carries_user_name(self, admin_client):
        client, user = admin_client
        data = client.get("/api/dashboard/summary").json()
        assert data["user_name"] == user.name

    def test_open_alerts_default_severity_keys(self, farmer_client):
        client, _user = farmer_client
        data = client.get("/api/dashboard/summary").json()
        sev = data["open_alerts"]["by_severity"]
        # Boş hesapta bile 3 anahtar bulunmalı (frontend kart için)
        assert set(sev.keys()) >= {"low", "medium", "critical"}
        assert all(isinstance(v, int) for v in sev.values())
