"""
MQTT Sensör Stream Dinleyicisi — İskelet
==========================================
Gerçek IoT cihazlardan (veya simülatörden) gelen sensör okumalarını MQTT
broker üzerinden dinleyip `SoilMoistureReading` tablosuna kaydeder.

Cycle 7'de Emirhan Günay tarafından geliştirilecek.

Mevcut durum: paho-mqtt kütüphanesi requirements.txt'te hazır; bu modül
MQTTListener sınıfı + on_message callback şablonu sağlar.

Tipik akış:
1. Cihaz (veya simülatör) → MQTT broker'a JSON mesaj publish:
   topic: `sfdap/sensors/{sensor_id}`
   payload: `{"moisture_percent": 45.2, "soil_temperature_c": 22.1, ...}`
2. Bu listener subscribe → mesaj geldiğinde DB'ye INSERT.
3. APScheduler ile periyodik istatistik (saatlik ortalama).

Genişletme adımları (Cycle 7 — Emirhan):
- MQTTListener.start() → broker'a connect + topic'lere subscribe
- _handle_message: payload validate → SoilMoistureReading yarat
- Hata yönetimi: bozuk JSON, eksik alan, geçersiz sensor_id
- Reconnect logic (broker düşerse)
- Health/deep'e MQTT durum entegrasyonu
- Test simülatörü: scripts/mqtt_publisher.py (random sensor mesajları gönderen)
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.models import Sensor, SoilMoistureReading

# MQTT topic deseni — wildcard ile tüm sensörleri dinle
MQTT_TOPIC_PATTERN = "sfdap/sensors/+"


class MQTTListener:
    """
    paho-mqtt tabanlı dinleyici. start() ile broker'a bağlanır,
    sensör mesajlarını dinler ve DB'ye kaydeder.

    Şu an iskelet — paho-mqtt importu Cycle 7'de aktif edilecek.
    """

    def __init__(
        self,
        broker_host: str | None = None,
        broker_port: int = 1883,
        client_id: str = "sfdap-listener",
    ):
        self.broker_host = broker_host or getattr(settings, "MQTT_BROKER_HOST", "localhost")
        self.broker_port = broker_port
        self.client_id = client_id
        self.client = None  # paho.mqtt.client.Client (Cycle 7)
        self.running = False

    def start(self) -> None:
        """Broker'a bağlan, topic'lere subscribe, loop başlat."""
        # TODO Cycle 7 — Emirhan:
        # import paho.mqtt.client as mqtt
        # self.client = mqtt.Client(client_id=self.client_id)
        # self.client.on_message = self._on_message
        # self.client.on_connect = self._on_connect
        # self.client.connect(self.broker_host, self.broker_port, keepalive=60)
        # self.client.subscribe(MQTT_TOPIC_PATTERN, qos=1)
        # self.client.loop_start()
        self.running = True
        logger.info(f"MQTT listener placeholder started (broker: {self.broker_host}:{self.broker_port})")

    def stop(self) -> None:
        """Loop'u durdur, broker bağlantısını kapat."""
        # TODO Cycle 7 — Emirhan:
        # if self.client:
        #     self.client.loop_stop()
        #     self.client.disconnect()
        self.running = False
        logger.info("MQTT listener stopped")

    def _on_connect(self, client, userdata, flags, rc) -> None:  # noqa: ANN001 — paho callback
        """Broker bağlantısı kurulduğunda çağrılır (Cycle 7'de aktif)."""
        if rc == 0:
            logger.info("MQTT broker'a baglanti kuruldu")
        else:
            logger.error(f"MQTT bağlantı hatası: rc={rc}")

    def _on_message(self, client, userdata, message) -> None:  # noqa: ANN001 — paho callback
        """Yeni mesaj geldiğinde DB'ye yaz."""
        try:
            payload = json.loads(message.payload.decode("utf-8"))
            sensor_id = self._extract_sensor_id(message.topic)
            if sensor_id is None:
                logger.warning(f"Geçersiz topic, sensor_id çıkarılamadı: {message.topic}")
                return
            with SessionLocal() as db:
                self._save_reading(db, sensor_id, payload)
        except json.JSONDecodeError:
            logger.warning(f"MQTT mesajı JSON parse edilemedi (topic={message.topic})")
        except Exception:
            logger.exception(f"MQTT mesaj işleme hatası (topic={message.topic})")

    @staticmethod
    def _extract_sensor_id(topic: str) -> int | None:
        """`sfdap/sensors/123` → 123"""
        parts = topic.split("/")
        if len(parts) >= 3 and parts[-1].isdigit():
            return int(parts[-1])
        return None

    def _save_reading(self, db: Session, sensor_id: int, payload: dict[str, Any]) -> None:
        """Sensör okumasını DB'ye kaydet — sensör ID doğrulanır."""
        sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
        if sensor is None:
            logger.warning(f"Bilinmeyen sensor_id={sensor_id}, mesaj göz ardı edildi")
            return
        reading = SoilMoistureReading(
            sensor_id=sensor_id,
            moisture_percent=float(payload.get("moisture_percent", 0)),
            depth_cm=sensor.depth_cm,
            soil_temperature_c=float(payload.get("soil_temperature_c", 0)),
            electrical_conductivity=float(payload.get("electrical_conductivity", 0)),
        )
        db.add(reading)
        db.commit()


# Global instance — uygulama başlangıcında start() çağrılır (lifespan)
mqtt_listener = MQTTListener()
