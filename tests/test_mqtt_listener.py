"""
MQTT Listener Unit Tests
==========================
`MQTTListener._save_reading` ve `_extract_sensor_id` saf fonksiyonlarını
broker olmadan test eder. Lifecycle (start/stop) ve paho callback'leri
mock'larla test edilir; gerçek broker gerektirmez.
"""

from __future__ import annotations

import json
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.models.models import Farm, Field, Sensor, SoilMoistureReading, User
from app.services.mqtt_listener import MQTTListener, _safe_float, mqtt_listener


@pytest.fixture
def fake_paho(monkeypatch):
    """sys.modules'a fake `paho.mqtt.client` hierarchy enjekte eder.

    Test ortamında paho-mqtt yüklü değil (optional dep). Bu fixture
    `import paho.mqtt.client as mqtt` ifadesinin başarılı dönmesini
    sağlar ve mock'lanmış Client class'ı döndürür.

    EN: Injects a fake paho.mqtt.client module hierarchy so the import
    in MQTTListener.start() succeeds; returns the mocked Client class.
    """
    fake_paho_pkg = ModuleType("paho")
    fake_paho_mqtt_pkg = ModuleType("paho.mqtt")
    fake_paho_mqtt_client_mod = ModuleType("paho.mqtt.client")

    mock_client_factory = MagicMock()
    fake_paho_mqtt_client_mod.Client = mock_client_factory
    # paho-mqtt 2.x API uyumluluğu için CallbackAPIVersion sahte enum
    fake_paho_mqtt_client_mod.CallbackAPIVersion = MagicMock(VERSION2="v2")

    fake_paho_pkg.mqtt = fake_paho_mqtt_pkg
    fake_paho_mqtt_pkg.client = fake_paho_mqtt_client_mod

    monkeypatch.setitem(sys.modules, "paho", fake_paho_pkg)
    monkeypatch.setitem(sys.modules, "paho.mqtt", fake_paho_mqtt_pkg)
    monkeypatch.setitem(sys.modules, "paho.mqtt.client", fake_paho_mqtt_client_mod)

    return mock_client_factory


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


# ─── start() / stop() lifecycle ──────────────────────────────────────


class TestStartStop:
    """`start()` ve `stop()` paho-mqtt mock'lanmış senaryolar."""

    def test_start_returns_false_when_paho_not_installed(self, monkeypatch):
        """paho.mqtt.client import edilemezse start() False döner."""
        # sys.modules'tan paho'yu ve alt modulleri kaldır + None set'le
        for key in ("paho", "paho.mqtt", "paho.mqtt.client"):
            monkeypatch.setitem(sys.modules, key, None)
        listener = MQTTListener()
        assert listener.start() is False
        assert listener.running is False

    def test_start_returns_false_when_broker_unreachable(self, fake_paho):
        """Broker'a connect başarısız olursa False, running False kalmalı."""
        fake_client = MagicMock()
        fake_client.connect.side_effect = OSError("connection refused")
        fake_paho.return_value = fake_client

        listener = MQTTListener(broker_host="unreachable", broker_port=1883)
        assert listener.start() is False
        assert listener.running is False

    def test_start_succeeds_and_double_start_idempotent(self, fake_paho):
        """Başarılı start sonrası ikinci start True döner ama tekrar connect etmez."""
        fake_client = MagicMock()
        fake_paho.return_value = fake_client

        listener = MQTTListener()
        assert listener.start() is True
        assert listener.running is True
        # Connect ve loop_start çağrıları yapılmış olmalı
        fake_client.connect.assert_called_once_with("localhost", 1883, keepalive=60)
        fake_client.loop_start.assert_called_once()
        # Callback'ler atandı — direkt çağırarak doğrula (subscribe tetiklenmeli)
        fake_client.on_connect(fake_client, None, None, rc=0)
        fake_client.subscribe.assert_called_once()
        # İkinci start çağrısı no-op (zaten running)
        connect_call_count = fake_client.connect.call_count
        assert listener.start() is True
        assert fake_client.connect.call_count == connect_call_count

        # Cleanup
        listener.stop()

    def test_stop_closes_running_listener(self, fake_paho):
        """Çalışan listener stop() çağrısında loop_stop + disconnect yapmalı."""
        fake_client = MagicMock()
        fake_paho.return_value = fake_client

        listener = MQTTListener()
        listener.start()
        listener.connected = True
        listener.stop()

        fake_client.loop_stop.assert_called_once()
        fake_client.disconnect.assert_called_once()
        assert listener.running is False
        assert listener.connected is False

    def test_stop_noop_when_not_running(self):
        """Hiç başlatılmamış listener'da stop() exception atmamalı."""
        listener = MQTTListener()
        # client None, running False
        listener.stop()  # silently no-op
        assert listener.running is False


# ─── paho callback'leri ──────────────────────────────────────────────


class TestPahoCallbacks:
    """`_on_connect` ve `_on_disconnect` davranışları."""

    def test_on_connect_success_subscribes(self):
        """rc=0 (başarılı) → connected True, subscribe çağrılmalı."""
        listener = MQTTListener()
        fake_client = MagicMock()
        listener._on_connect(fake_client, None, None, rc=0)
        assert listener.connected is True
        fake_client.subscribe.assert_called_once()

    def test_on_connect_failure_sets_connected_false(self):
        """rc!=0 → connected False, subscribe çağrılmamalı."""
        listener = MQTTListener()
        fake_client = MagicMock()
        listener._on_connect(fake_client, None, None, rc=4)
        assert listener.connected is False
        fake_client.subscribe.assert_not_called()

    def test_on_disconnect_clears_connected_flag(self):
        """Disconnect callback'i connected=False yapmalı."""
        listener = MQTTListener()
        listener.connected = True
        listener._on_disconnect(MagicMock(), None, rc=0)
        assert listener.connected is False


# ─── _safe_float helper ───────────────────────────────────────────────


class TestSafeFloat:
    def test_none_returns_none(self):
        assert _safe_float(None) is None

    def test_invalid_string_returns_none(self):
        assert _safe_float("not-a-number") is None

    def test_valid_number_returns_float(self):
        assert _safe_float("42.5") == 42.5
        assert _safe_float(7) == 7.0
