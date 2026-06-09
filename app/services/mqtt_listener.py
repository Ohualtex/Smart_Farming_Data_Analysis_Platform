"""
MQTT Sensor Stream Dinleyicisi
================================
IoT cihazlarından (veya `scripts/mqtt_publisher.py` simülatöründen) MQTT
broker üzerinden gelen sensör okumalarını dinler ve `SoilMoistureReading`
tablosuna yazar.

Akış:
1. Cihaz → broker'a publish:
   topic   : `sfdap/sensors/{sensor_id}`
   payload : `{"moisture_percent": 45.2, "soil_temperature_c": 22.1, ...}`
2. Listener subscribe → mesaj geldiğinde DB INSERT.
3. `start()` lifespan'da çağrılır; `MQTT_ENABLED=true` ve broker erişilebilir
   ise aktif olur, aksi halde no-op (development için broker zorunlu değil).

Konfigurasyon (env / settings):
- MQTT_ENABLED        — true/false (default false; testlerde patlamasın diye)
- MQTT_BROKER_HOST    — default "localhost"
- MQTT_BROKER_PORT    — default 1883
- MQTT_CLIENT_ID      — default "sfdap-listener"
"""

from __future__ import annotations

import json
import threading
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.models import Sensor, SoilMoistureReading

MQTT_TOPIC_PATTERN = "sfdap/sensors/+"


class MQTTListener:
    """
    paho-mqtt tabanlı sensör akışı dinleyicisi.

    `start()` broker'a bağlanır ve topic'lere subscribe olur. Bağlantı veya
    paho-mqtt yüklü değilse listener sessizce devre dışı kalır
    (development'ta broker olmadan da uygulama çalışmalı).
    """

    def __init__(
        self,
        broker_host: str | None = None,
        broker_port: int | None = None,
        client_id: str | None = None,
    ):
        self.broker_host = broker_host or getattr(settings, "MQTT_BROKER_HOST", "localhost")
        self.broker_port = broker_port or getattr(settings, "MQTT_BROKER_PORT", 1883)
        self.client_id = client_id or getattr(settings, "MQTT_CLIENT_ID", "sfdap-listener")
        self.client: Any = None
        self.running = False
        self.connected = False
        self._lock = threading.Lock()

    def start(self) -> bool:
        """Broker'a bağlan ve loop'u başlat. Başarısız olursa False."""
        with self._lock:
            if self.running:
                return True
            try:
                import paho.mqtt.client as mqtt
            except ImportError:
                logger.warning("paho-mqtt yuklu degil, MQTT listener devre disi.")
                return False

            try:
                self.client = mqtt.Client(client_id=self.client_id, clean_session=True)
            except (TypeError, AttributeError):
                # paho-mqtt 2.x — yeni API: Client(CallbackAPIVersion.VERSION2, ...)
                try:
                    self.client = mqtt.Client(
                        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                        client_id=self.client_id,
                    )
                except Exception:
                    logger.exception("MQTT client olusturulamadi")
                    return False

            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message

            try:
                self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            except (OSError, ConnectionRefusedError) as exc:
                logger.warning(f"MQTT broker'a baglanti kurulamadi: {exc}")
                return False

            self.client.loop_start()
            self.running = True
            logger.info(f"MQTT listener basladi (broker: {self.broker_host}:{self.broker_port})")
            return True

    def stop(self) -> None:
        """Loop'u durdur, bağlantıyı kapat."""
        with self._lock:
            if not self.running or self.client is None:
                self.running = False
                return
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:
                logger.exception("MQTT stop sirasinda hata")
            finally:
                self.running = False
                self.connected = False
                logger.info("MQTT listener durduruldu")

    def status(self) -> dict[str, Any]:
        """`/api/health/deep` için durum özeti."""
        return {
            "enabled": self.running,
            "connected": self.connected,
            "broker": f"{self.broker_host}:{self.broker_port}",
        }

    # ─── paho callback'leri ────────────────────────────────────────
    def _on_connect(self, client, userdata, flags, rc, *args, **kwargs) -> None:  # noqa: ANN001
        if rc == 0:
            self.connected = True
            client.subscribe(MQTT_TOPIC_PATTERN, qos=1)
            logger.info(f"MQTT broker'a baglandi, subscribe: {MQTT_TOPIC_PATTERN}")
        else:
            self.connected = False
            logger.error(f"MQTT baglanti hatasi rc={rc}")

    def _on_disconnect(self, client, userdata, rc, *args, **kwargs) -> None:  # noqa: ANN001
        self.connected = False
        if rc != 0:
            logger.warning(f"MQTT baglantisi beklenmedik sekilde dustu (rc={rc})")

    def _on_message(self, client, userdata, message) -> None:  # noqa: ANN001
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.warning(f"MQTT JSON parse edilemedi (topic={message.topic})")
            return
        sensor_id = self._extract_sensor_id(message.topic)
        if sensor_id is None:
            logger.warning(f"Topic'ten sensor_id cikartilamadi: {message.topic}")
            return
        try:
            with SessionLocal() as db:
                self._save_reading(db, sensor_id, payload)
        except Exception:
            logger.exception(f"MQTT mesaj DB'ye yazilamadi (topic={message.topic})")

    # ─── yardımcılar ───────────────────────────────────────────────
    @staticmethod
    def _extract_sensor_id(topic: str) -> int | None:
        """`sfdap/sensors/123` → 123"""
        parts = topic.split("/")
        if len(parts) >= 3 and parts[-1].isdigit():
            return int(parts[-1])
        return None

    @staticmethod
    def _save_reading(db: Session, sensor_id: int, payload: dict[str, Any]) -> bool:
        """Payload'ı validate edip okuma kaydını ekle. Başarılıysa True."""
        sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
        if sensor is None:
            logger.warning(f"Bilinmeyen sensor_id={sensor_id}, mesaj atlandi")
            return False
        # Audit fix (#15): moisture_percent eksik/None ise 0'a düşürmek yerine
        # okumayı atla — aksi halde sahte %0 değeri sınır kontrolünü geçip kaydedilir.
        raw_moisture = payload.get("moisture_percent")
        if raw_moisture is None:
            logger.warning(f"moisture_percent eksik, okuma atlandi: {payload!r}")
            return False
        try:
            moisture = float(raw_moisture)
        except (TypeError, ValueError):
            logger.warning(f"Gecersiz moisture_percent: {payload!r}")
            return False
        if not 0 <= moisture <= 100:
            logger.warning(f"moisture_percent={moisture} sinir disi, atlandi")
            return False
        reading = SoilMoistureReading(
            sensor_id=sensor_id,
            moisture_percent=moisture,
            depth_cm=sensor.depth_cm,
            soil_temperature_c=_safe_float(payload.get("soil_temperature_c")),
            electrical_conductivity=_safe_float(payload.get("electrical_conductivity")),
        )
        db.add(reading)
        db.commit()
        return True


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


mqtt_listener = MQTTListener()
