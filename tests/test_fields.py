"""
Field Detail Endpoint Tests — REBUILD Faz 3
=============================================
`GET /api/fields/{id}` aggregated tarla detayı + `/readings` zaman serisi.

Kapsama matriksi:
    anon              → 401
    farmer (own)      → 200 + aggregation doğru
    farmer (other)    → 403
    farmer (missing)  → 404
    admin             → bypass (başka kullanıcının tarlası dahil)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models.models import (
    CropType,
    Farm,
    Field,
    IrrigationSchedule,
    PlantHealthImage,
    Sensor,
    SoilAnalysis,
    SoilMoistureReading,
    SystemAlert,
)


def _seed_field_with_context(db, user_id: int, *, moisture: float = 25.0):
    """Farmer'a ait dolu bir tarla kur: crop + sensor + reading + irrigation
    + disease + soil + alert. (farm, field, sensor) döner."""
    crop = CropType(name="Buğday", scientific_name="Triticum", water_need_mm_per_day=4.5)
    db.add(crop)
    db.flush()
    farm = Farm(user_id=user_id, name="Ahmet Çiftliği", region="İç Anadolu", city="Konya")
    db.add(farm)
    db.flush()
    field = Field(
        farm_id=farm.id,
        name="Tarla A",
        soil_type="killi",
        area_hectares=2.5,
        elevation_m=1020.0,
        crop_id=crop.id,
    )
    db.add(field)
    db.flush()
    sensor = Sensor(field_id=field.id, sensor_type="soil_moisture", serial_number=f"SN-{user_id}-A")
    db.add(sensor)
    db.flush()
    db.add(
        SoilMoistureReading(
            sensor_id=sensor.id,
            moisture_percent=moisture,
            soil_temperature_c=18.0,
            reading_timestamp=datetime.now(UTC) - timedelta(hours=1),
        )
    )
    db.add(
        IrrigationSchedule(
            field_id=field.id,
            scheduled_date=datetime.now(UTC) - timedelta(days=1),
            water_amount_liters=200.0,
            duration_min=45,
            status="completed",
            source="model",
        )
    )
    db.add(
        PlantHealthImage(
            field_id=field.id,
            image_url="leaf.jpg",
            captured_at=datetime.now(UTC) - timedelta(hours=3),
            diagnosis="leaf_rust",
            confidence_score=0.88,
            severity="moderate",
        )
    )
    db.add(
        SoilAnalysis(
            field_id=field.id,
            analysis_date=datetime.now(UTC) - timedelta(days=10),
            ph_level=6.8,
            nitrogen_mg_kg=45.0,
            phosphorus_mg_kg=22.0,
            potassium_mg_kg=180.0,
            texture_class="killi-tınlı",
        )
    )
    db.add(
        SystemAlert(
            farm_id=farm.id,
            field_id=field.id,
            alert_type="sensor_anomaly",
            severity="critical",
            message="Nem kritik düşük",
            is_resolved=False,
        )
    )
    db.commit()
    return farm, field, sensor


# ─── Anon erişim ───────────────────────────────────────────────


class TestFieldDetailAnon:
    def test_anon_returns_401(self, anon_client):
        resp = anon_client.get("/api/fields/1")
        assert resp.status_code == 401


# ─── Farmer scope ──────────────────────────────────────────────


class TestFieldDetailFarmerScope:
    def test_farmer_own_field_returns_full_detail(self, farmer_client, db):
        client, user = farmer_client
        _farm, field, _sensor = _seed_field_with_context(db, user.id)
        resp = client.get(f"/api/fields/{field.id}")
        assert resp.status_code == 200
        data = resp.json()
        # Çekirdek
        assert data["name"] == "Tarla A"
        assert data["soil_type"] == "killi"
        assert data["area_hectares"] == 2.5
        assert data["farm_name"] == "Ahmet Çiftliği"
        assert data["region"] == "İç Anadolu"
        # Crop
        assert data["crop"]["name"] == "Buğday"
        assert data["crop"]["water_need_mm_per_day"] == 4.5
        # Moisture (25 < 30 → dry)
        assert data["moisture_status"] == "dry"
        assert data["avg_moisture_percent"] == 25.0
        # Koleksiyonlar
        assert len(data["sensors"]) == 1
        assert data["sensors"][0]["latest_moisture_percent"] == 25.0
        assert data["sensors"][0]["latest_soil_temperature_c"] == 18.0
        assert len(data["recent_irrigations"]) == 1
        assert data["recent_irrigations"][0]["water_amount_liters"] == 200.0
        assert len(data["disease_history"]) == 1
        assert data["disease_history"][0]["diagnosis"] == "leaf_rust"
        assert len(data["soil_analyses"]) == 1
        assert data["soil_analyses"][0]["ph_level"] == 6.8
        assert len(data["open_alerts"]) == 1
        assert data["open_alerts"][0]["severity"] == "critical"

    def test_farmer_other_field_returns_403(self, farmer_client, db):
        client, _user = farmer_client
        # Başka kullanıcıya ait tarla
        _farm, other_field, _sensor = _seed_field_with_context(db, 9999)
        resp = client.get(f"/api/fields/{other_field.id}")
        assert resp.status_code == 403

    def test_farmer_missing_field_returns_404(self, farmer_client):
        client, _user = farmer_client
        resp = client.get("/api/fields/99999")
        assert resp.status_code == 404

    def test_farmer_field_no_data_moisture_no_data(self, farmer_client, db):
        client, user = farmer_client
        farm = Farm(user_id=user.id, name="Boş Çiftlik", region="Ege")
        db.add(farm)
        db.flush()
        field = Field(farm_id=farm.id, name="Boş Tarla", soil_type="kumlu")
        db.add(field)
        db.commit()
        resp = client.get(f"/api/fields/{field.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["moisture_status"] == "no_data"
        assert data["avg_moisture_percent"] is None
        assert data["crop"] is None
        assert data["sensors"] == []
        assert data["recent_irrigations"] == []
        assert data["disease_history"] == []
        assert data["open_alerts"] == []

    def test_resolved_alert_not_in_open_alerts(self, farmer_client, db):
        client, user = farmer_client
        farm = Farm(user_id=user.id, name="Ç", region="Ege")
        db.add(farm)
        db.flush()
        field = Field(farm_id=farm.id, name="T", soil_type="killi")
        db.add(field)
        db.flush()
        db.add(
            SystemAlert(
                farm_id=farm.id,
                field_id=field.id,
                alert_type="x",
                severity="low",
                message="çözüldü",
                is_resolved=True,
            )
        )
        db.commit()
        data = client.get(f"/api/fields/{field.id}").json()
        assert data["open_alerts"] == []


# ─── System scope (admin bypass) ───────────────────────────────


class TestFieldDetailSystemScope:
    def test_admin_sees_other_users_field(self, admin_client, db):
        client, _user = admin_client
        _farm, field, _sensor = _seed_field_with_context(db, 9999)
        resp = client.get(f"/api/fields/{field.id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Tarla A"

    def test_developer_sees_other_users_field(self, developer_client, db):
        client, _user = developer_client
        _farm, field, _sensor = _seed_field_with_context(db, 9999)
        assert client.get(f"/api/fields/{field.id}").status_code == 200


# ─── Multi-sensor N+1 fix verification (v3-3 → v4-1 coverage) ──


class TestFieldDetailMultiSensor:
    """v4-1: v3-3 N+1 fix (batch latest_by_sensor) çoklu sensor'da çalışır.

    Önceki kod her sensor için ayrı query yapardı (1+N); yeni kod tek
    IN-list query + Python grouping (2 toplam). Sonuç: her sensor en
    yeni okumayı doğru gösterir.
    """

    def test_multi_sensor_each_shows_own_latest(self, farmer_client, db):
        from datetime import UTC, datetime, timedelta

        from app.models.models import Farm, Field, Sensor, SoilMoistureReading

        client, user = farmer_client
        farm = Farm(user_id=user.id, name="Çoklu", region="Ege")
        db.add(farm)
        db.flush()
        field = Field(farm_id=farm.id, name="MultiSensorTarla", soil_type="killi")
        db.add(field)
        db.flush()
        # 3 sensor — her biri farklı moisture değeri ile en yeni okuma
        sensors_data = [(40.0, 1), (25.0, 2), (60.0, 3)]
        sensor_ids = []
        now = datetime.now(UTC)
        for moisture, idx in sensors_data:
            s = Sensor(field_id=field.id, sensor_type="soil_moisture", serial_number=f"SN-{idx}")
            db.add(s)
            db.flush()
            sensor_ids.append(s.id)
            # Eski okuma (gürültü)
            db.add(
                SoilMoistureReading(
                    sensor_id=s.id,
                    moisture_percent=10.0,
                    reading_timestamp=now - timedelta(days=2),
                )
            )
            # En yeni okuma
            db.add(
                SoilMoistureReading(
                    sensor_id=s.id,
                    moisture_percent=moisture,
                    reading_timestamp=now - timedelta(minutes=idx),
                )
            )
        db.commit()

        resp = client.get(f"/api/fields/{field.id}")
        assert resp.status_code == 200
        sensors_resp = resp.json()["sensors"]
        assert len(sensors_resp) == 3
        # Her sensor'ın latest_moisture_percent eski 10.0 değil, kendi en yenisi
        latest_by_id = {s["id"]: s["latest_moisture_percent"] for s in sensors_resp}
        assert latest_by_id[sensor_ids[0]] == 40.0
        assert latest_by_id[sensor_ids[1]] == 25.0
        assert latest_by_id[sensor_ids[2]] == 60.0


# ─── Readings zaman serisi ─────────────────────────────────────


class TestFieldReadings:
    def test_readings_chronological_order(self, farmer_client, db):
        client, user = farmer_client
        _farm, field, sensor = _seed_field_with_context(db, user.id)
        # Ek okumalar — farklı zamanlar
        db.add(
            SoilMoistureReading(
                sensor_id=sensor.id,
                moisture_percent=30.0,
                reading_timestamp=datetime.now(UTC) - timedelta(hours=5),
            )
        )
        db.add(
            SoilMoistureReading(
                sensor_id=sensor.id,
                moisture_percent=35.0,
                reading_timestamp=datetime.now(UTC) - timedelta(hours=10),
            )
        )
        db.commit()
        resp = client.get(f"/api/fields/{field.id}/readings")
        assert resp.status_code == 200
        rows = resp.json()
        assert len(rows) == 3
        # Kronolojik: en eski önce
        timestamps = [r["reading_timestamp"] for r in rows]
        assert timestamps == sorted(timestamps)

    def test_readings_other_field_403(self, farmer_client, db):
        client, _user = farmer_client
        _farm, other_field, _sensor = _seed_field_with_context(db, 9999)
        assert client.get(f"/api/fields/{other_field.id}/readings").status_code == 403

    def test_readings_respects_limit(self, farmer_client, db):
        client, user = farmer_client
        _farm, field, sensor = _seed_field_with_context(db, user.id)
        for i in range(8):
            db.add(
                SoilMoistureReading(
                    sensor_id=sensor.id,
                    moisture_percent=20.0 + i,
                    reading_timestamp=datetime.now(UTC) - timedelta(hours=i + 2),
                )
            )
        db.commit()
        resp = client.get(f"/api/fields/{field.id}/readings?limit=3")
        assert resp.status_code == 200
        assert len(resp.json()) == 3


# ─── REBUILD Faz 4 — CRUD write testleri ──────────────────────


class TestFieldWrite:
    """POST/PATCH/DELETE /api/fields — rol-aware + sensör cascade guard."""

    def test_farmer_creates_field_on_own_farm(self, farmer_client, db):
        client, user = farmer_client
        farm = Farm(user_id=user.id, name="Çiftlik", region="Ege")
        db.add(farm)
        db.commit()
        r = client.post(
            "/api/fields",
            json={"farm_id": farm.id, "name": "Yeni Tarla", "soil_type": "killi", "area_hectares": 2.0},
        )
        assert r.status_code == 201
        assert r.json()["name"] == "Yeni Tarla"

    def test_farmer_cannot_create_on_others_farm_403(self, farmer_client, db):
        client, _ = farmer_client
        other = Farm(user_id=9999, name="Başka", region="Marmara")
        db.add(other)
        db.commit()
        r = client.post("/api/fields", json={"farm_id": other.id, "name": "Hack"})
        assert r.status_code == 403

    def test_create_on_missing_farm_404(self, farmer_client):
        client, _ = farmer_client
        r = client.post("/api/fields", json={"farm_id": 999999, "name": "X"})
        assert r.status_code == 404

    def test_overseer_cannot_create_403(self, overseer_client, db):
        client, _ = overseer_client
        farm = Farm(user_id=1, name="Ç", region="Ege")
        db.add(farm)
        db.commit()
        r = client.post("/api/fields", json={"farm_id": farm.id, "name": "X"})
        assert r.status_code == 403

    def test_anon_cannot_create_401(self, anon_client):
        r = anon_client.post("/api/fields", json={"farm_id": 1, "name": "X"})
        assert r.status_code == 401

    def test_farmer_updates_own_field(self, farmer_client, db):
        client, user = farmer_client
        farm = Farm(user_id=user.id, name="Ç", region="Ege")
        db.add(farm)
        db.flush()
        field = Field(farm_id=farm.id, name="Eski", soil_type="killi")
        db.add(field)
        db.commit()
        r = client.patch(f"/api/fields/{field.id}", json={"name": "Yeni", "soil_type": "tınlı"})
        assert r.status_code == 200
        assert r.json()["name"] == "Yeni"
        assert r.json()["soil_type"] == "tınlı"

    def test_farmer_cannot_update_others_field_403(self, farmer_client, db):
        client, _ = farmer_client
        _farm, other_field, _sensor = _seed_field_with_context(db, 9999)
        r = client.patch(f"/api/fields/{other_field.id}", json={"name": "Hack"})
        assert r.status_code == 403

    def test_delete_field_without_sensors_204(self, farmer_client, db):
        client, user = farmer_client
        farm = Farm(user_id=user.id, name="Ç", region="Ege")
        db.add(farm)
        db.flush()
        field = Field(farm_id=farm.id, name="Boş Tarla", soil_type="killi")
        db.add(field)
        db.commit()
        fid = field.id
        r = client.delete(f"/api/fields/{fid}")
        assert r.status_code == 204
        assert db.query(Field).filter(Field.id == fid).first() is None

    def test_delete_field_with_sensors_409(self, farmer_client, db):
        client, user = farmer_client
        # _seed_field_with_context owned by farmer → has 1 sensor
        _farm, field, _sensor = _seed_field_with_context(db, user.id)
        r = client.delete(f"/api/fields/{field.id}")
        assert r.status_code == 409
        assert db.query(Field).filter(Field.id == field.id).first() is not None

    def test_delete_missing_field_404(self, farmer_client):
        client, _ = farmer_client
        assert client.delete("/api/fields/999999").status_code == 404
