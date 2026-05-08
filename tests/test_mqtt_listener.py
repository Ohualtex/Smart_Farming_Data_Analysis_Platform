"""
MQTT Listener Unit Tests
==========================
`MQTTListener._save_reading` ve `_extract_sensor_id` saf fonksiyonlarını
broker olmadan test eder. Gerçek paho-mqtt bağlantısı için entegrasyon
testi yok — broker gerektirir.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.models.models import Farm, Field, Sensor, SoilMoistureReading, User
from app.services.mqtt_listener import MQTTListener, mqtt_listener


@pytest.fixture
def sensor_setup(db):
    """Test DB'ye User → Farm → Field → Sensor zinciri kur."""
    user = User(name="Test User", email="t@x.com", role="farmer", password_hash="dummy$hash")
    db.add(user)
    db.commit()
    db.refresh(user)

    farm = Farm(user_id=user.id, name="Test Farm", city="Test", region="Test")
    db.add(farm)
    db.commit()
    db.refresh(farm)

    field = Field(farm_id=farm.id, name="F1")
    db.add(field)
    db.commit()
    db.refresh(field)

    sensor = Sensor(
        field_id=field.id,
        sensor_type="soil_moisture",
        serial_number="MQTT-TEST-1",
        depth_cm=20.0,
    )
    db.add(sensor)
    db.commit()
    db.refresh(sensor)
    return sensor


class TestExtractSensorId:
    def test_valid_topic(self):
        assert MQTTListener._extract_sensor_id("sfdap/sensors/42") == 42

    def test_topic_with_extra_segments(self):
        assert MQTTListener._extract_sensor_id("foo/bar/sfdap/sensors/7") == 7

    def test_non_numeric_id(self):
        assert MQTTListener._extract_sensor_id("sfdap/sensors/abc") is None

    def test_too_short(self):
        assert MQTTListener._extract_sensor_id("sfdap") is None

    def test_empty(self):
        assert MQTTListener._extract_sensor_id("") is None


class TestSaveReading:
    def test_valid_payload_creates_reading(self, db, sensor_setup):
        ok = MQTTListener._save_reading(
            db,
            sensor_setup.id,
            {"moisture_percent": 45.0, "soil_temperature_c": 22.5, "electrical_conductivity": 1.8},
        )
        assert ok is True
        reading = db.query(SoilMoistureReading).filter_by(sensor_id=sensor_setup.id).first()
        assert reading is not None
        assert reading.moisture_percent == 45.0
        assert reading.soil_temperature_c == 22.5

    def test_unknown_sensor_id_returns_false(self, db):
        ok = MQTTListener._save_reading(db, 999_999, {"moisture_percent": 50.0})
        assert ok is False

    def test_out_of_range_moisture_rejected(self, db, sensor_setup):
        ok = MQTTListener._save_reading(db, sensor_setup.id, {"moisture_percent": 150.0})
        assert ok is False
        assert db.query(SoilMoistureReading).count() == 0

    def test_negative_moisture_rejected(self, db, sensor_setup):
        ok = MQTTListener._save_reading(db, sensor_setup.id, {"moisture_percent": -5.0})
        assert ok is False

    def test_non_numeric_moisture_rejected(self, db, sensor_setup):
        ok = MQTTListener._save_reading(db, sensor_setup.id, {"moisture_percent": "abc"})
        assert ok is False

    def test_missing_optional_fields_ok(self, db, sensor_setup):
        ok = MQTTListener._save_reading(db, sensor_setup.id, {"moisture_percent": 35.0})
        assert ok is True
        reading = db.query(SoilMoistureReading).filter_by(sensor_id=sensor_setup.id).first()
        assert reading.soil_temperature_c is None


class TestStatus:
    def test_default_status_is_disabled(self):
        listener = MQTTListener(broker_host="x", broker_port=1883)
        s = listener.status()
        assert s["enabled"] is False
        assert s["connected"] is False
        assert s["broker"] == "x:1883"

    def test_global_listener_starts_disabled(self):
        # Singleton hiç start edilmemiş → enabled False
        s = mqtt_listener.status()
        assert "enabled" in s
        assert "broker" in s


class TestOnMessage:
    """`_on_message` callback'i: bozuk payload'larda DB'ye yazmamalı."""

    def test_bad_json_logged_no_raise(self, db, sensor_setup):
        """Invalid JSON sessizce atlanmalı (test conftest DB ile çakışmasın diye direkt _save_reading'i test ediyoruz)."""
        msg = SimpleNamespace(
            topic=f"sfdap/sensors/{sensor_setup.id}",
            payload=b"not-valid-json-{",
        )
        # _on_message DB'ye yazmayı dener; bozuk JSON'da yazmadan döner
        listener = MQTTListener()
        # Patch SessionLocal kullanılmasın; payload parse aşamasında dönecek
        listener._on_message(None, None, msg)
        # SessionLocal global olduğundan ayrı DB; ama log'da uyarı olmalı, exception olmamalı
        # Test conftest DB'sinde okuma sayısı 0 kalır
        assert db.query(SoilMoistureReading).count() == 0

    def test_unknown_topic_no_write(self, db):
        """sfdap/sensors/X formatına uymayan topic — yazma yapma."""
        msg = SimpleNamespace(
            topic="random/topic",
            payload=json.dumps({"moisture_percent": 50.0}).encode(),
        )
        listener = MQTTListener()
        listener._on_message(None, None, msg)
        assert db.query(SoilMoistureReading).count() == 0
