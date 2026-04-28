"""
Analytics Endpoint Testleri
=============================
/api/analytics/summary endpoint'i için kapsamlı testler.

Miraç Duran — Cycle 6 Görevi
"""

from datetime import datetime, timedelta, timezone

from app.models.models import (
    Farm,
    Field,
    IrrigationSchedule,
    Sensor,
    SoilMoistureReading,
    User,
    WeatherData,
)


def _seed_demo_data(db):
    """Test için minimum demo veri oluşturur."""
    user = User(
        name="Test User", email="test@sfdap.com",
        password_hash="hashed_pw", role="farmer",
    )
    db.add(user)
    db.flush()

    farm = Farm(
        user_id=user.id, name="Test Çiftliği",
        location_lat=37.0, location_lng=35.0,
        area_hectares=50.0, city="Adana", region="Akdeniz",
    )
    db.add(farm)
    db.flush()

    field = Field(
        farm_id=farm.id, name="Test Tarlası",
        area_hectares=20.0, soil_type="killi-tınlı",
    )
    db.add(field)
    db.flush()

    # 2 farklı tipte sensör
    sensor1 = Sensor(
        field_id=field.id, sensor_type="soil_moisture",
        serial_number="TEST-SM-001", status="active",
    )
    sensor2 = Sensor(
        field_id=field.id, sensor_type="soil_temperature",
        serial_number="TEST-ST-001", status="active",
    )
    db.add_all([sensor1, sensor2])
    db.flush()

    # Sensör okumaları
    now = datetime.now(timezone.utc)
    for i in range(10):
        db.add(SoilMoistureReading(
            sensor_id=sensor1.id,
            reading_timestamp=now - timedelta(days=i),
            moisture_percent=40.0 + i,
            soil_temperature_c=20.0 + i * 0.5,
        ))
    db.flush()

    # Hava durumu kayıtları
    for i in range(10):
        db.add(WeatherData(
            farm_id=farm.id,
            recorded_at=now - timedelta(days=i),
            temperature_c=22.0 + i * 0.3,
            humidity_percent=55.0 + i,
            precipitation_mm=i * 0.5,
            wind_speed_kmh=10.0 + i,
        ))
    db.flush()

    # Sulama programları
    statuses = ["completed", "completed", "pending", "cancelled"]
    for i, status in enumerate(statuses):
        db.add(IrrigationSchedule(
            field_id=field.id,
            scheduled_date=now - timedelta(days=i * 3),
            duration_min=60,
            water_amount_liters=2000.0,
            source="model",
            status=status,
        ))
    db.flush()
    db.commit()

    return {"user": user, "farm": farm, "field": field, "sensors": [sensor1, sensor2]}


# ─── TESTLER ─────────────────────────────────────────────────────


def test_analytics_summary_empty(client):
    """Boş veritabanında analytics endpoint'i 200 döner."""
    response = client.get("/api/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["counts"]["farms"] == 0
    assert data["counts"]["sensors"] == 0
    assert data["sensor_type_distribution"] == []
    assert data["farm_weather_comparison"] == []
    assert data["irrigation_status_distribution"] == []
    assert "npk_profiles" in data
    assert len(data["npk_profiles"]) == 8


def test_analytics_summary_with_data(client, db):
    """Demo veri ile analytics endpoint'i doğru istatistik döner."""
    _seed_demo_data(db)

    response = client.get("/api/analytics/summary")
    assert response.status_code == 200
    data = response.json()

    # Sayaçlar
    assert data["counts"]["farms"] == 1
    assert data["counts"]["fields"] == 1
    assert data["counts"]["sensors"] == 2
    assert data["counts"]["readings"] == 10
    assert data["counts"]["weather_records"] == 10
    assert data["counts"]["irrigation_schedules"] == 4


def test_analytics_sensor_type_distribution(client, db):
    """Sensör tipi dağılımı doğru döner."""
    _seed_demo_data(db)

    response = client.get("/api/analytics/summary")
    data = response.json()

    dist = data["sensor_type_distribution"]
    assert len(dist) == 2

    types = {d["type"]: d["count"] for d in dist}
    assert types["soil_moisture"] == 1
    assert types["soil_temperature"] == 1


def test_analytics_farm_weather_comparison(client, db):
    """Çiftlik bazlı hava durumu karşılaştırması doğru döner."""
    _seed_demo_data(db)

    response = client.get("/api/analytics/summary")
    data = response.json()

    comparison = data["farm_weather_comparison"]
    assert len(comparison) == 1
    assert comparison[0]["city"] == "Adana"
    assert comparison[0]["temperature"]["avg"] is not None
    assert comparison[0]["temperature"]["min"] <= comparison[0]["temperature"]["max"]
    assert comparison[0]["record_count"] == 10


def test_analytics_irrigation_status(client, db):
    """Sulama durumu dağılımı doğru döner."""
    _seed_demo_data(db)

    response = client.get("/api/analytics/summary")
    data = response.json()

    dist = data["irrigation_status_distribution"]
    statuses = {d["status"]: d["count"] for d in dist}
    assert statuses["completed"] == 2
    assert statuses["pending"] == 1
    assert statuses["cancelled"] == 1


def test_analytics_days_parameter(client, db):
    """days parametresi ile filtreleme doğru çalışır."""
    _seed_demo_data(db)

    response = client.get("/api/analytics/summary?days=3")
    assert response.status_code == 200
    data = response.json()
    assert data["period_days"] == 3


def test_analytics_daily_trends(client, db):
    """Günlük trend verileri çiftlik bazlı döner."""
    _seed_demo_data(db)

    response = client.get("/api/analytics/summary")
    data = response.json()

    trends = data["daily_trends"]
    assert len(trends) >= 1
    assert trends[0]["city"] == "Adana"
    assert len(trends[0]["days"]) > 0
    assert "temp_avg" in trends[0]["days"][0]
    assert "humidity_avg" in trends[0]["days"][0]


def test_analytics_sensor_reading_stats(client, db):
    """Sensör okuma istatistikleri doğru hesaplanır."""
    _seed_demo_data(db)

    response = client.get("/api/analytics/summary")
    data = response.json()

    stats = data["sensor_reading_stats"]
    assert stats["total_readings"] == 10
    assert stats["moisture"]["avg"] is not None
    assert stats["moisture"]["min"] <= stats["moisture"]["max"]
    assert stats["soil_temperature"]["avg"] is not None
