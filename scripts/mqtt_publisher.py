"""
MQTT Sensor Publisher (Simulator)
===================================
SFDAP'in MQTT listener'ını test etmek için sensör cihazlarını simüle eden
publisher. Belirli bir aralıkta rastgele toprak nem/sıcaklık değerleri
üretip `sfdap/sensors/{sensor_id}` topic'ine publish eder.

Kullanım:
    # Lokal mosquitto broker (1883) ile, sensor_id=1, 5 sn aralık
    python scripts/mqtt_publisher.py --sensor-id 1 --interval 5

    # Birden fazla sensör (1..5) round-robin
    python scripts/mqtt_publisher.py --sensor-ids 1,2,3,4,5 --interval 2

API tarafı:
    1. Bir broker çalıştır (örn: `docker run -p 1883:1883 eclipse-mosquitto`).
    2. .env'e: `MQTT_ENABLED=true`, `MQTT_BROKER_HOST=localhost`.
    3. `make run` → listener `app.main:lifespan`'da otomatik bağlanır.
    4. Bu script'i çalıştır → DB'de okumaların biriktiğini gör.
"""

from __future__ import annotations

import argparse
import json
import random
import signal
import sys
import time
from datetime import UTC, datetime

try:
    import paho.mqtt.client as mqtt
except ImportError:
    sys.exit("paho-mqtt yuklu degil. `pip install paho-mqtt` ile yukleyin.")


def random_payload() -> dict:
    """Sensör cihazını taklit eden rastgele ama tutarlı payload."""
    return {
        "moisture_percent": round(random.uniform(20, 75), 1),
        "soil_temperature_c": round(random.uniform(10, 30), 1),
        "electrical_conductivity": round(random.uniform(0.8, 4.0), 2),
        "ts": datetime.now(UTC).isoformat(),
    }


def parse_sensor_ids(arg: str) -> list[int]:
    return [int(x.strip()) for x in arg.split(",") if x.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="SFDAP MQTT sensor simulator")
    parser.add_argument("--host", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--sensor-id", type=int, help="Tek sensör için ID")
    parser.add_argument(
        "--sensor-ids",
        type=parse_sensor_ids,
        default=[1],
        help="Round-robin sensör listesi (örn. 1,2,3)",
    )
    parser.add_argument("--interval", type=float, default=5.0, help="Mesajlar arası saniye")
    parser.add_argument("--count", type=int, default=0, help="Toplam mesaj (0 = sonsuz)")
    args = parser.parse_args()

    sensor_ids = [args.sensor_id] if args.sensor_id else args.sensor_ids
    if not sensor_ids:
        sys.exit("--sensor-id veya --sensor-ids bos olamaz")

    try:
        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    except (TypeError, AttributeError):
        client = mqtt.Client()

    try:
        client.connect(args.host, args.port, keepalive=60)
    except (OSError, ConnectionRefusedError) as exc:
        sys.exit(f"Broker'a baglanilamadi ({args.host}:{args.port}): {exc}")

    client.loop_start()
    print(f"[mqtt_publisher] {args.host}:{args.port}'a baglandi, sensorler: {sensor_ids}")

    stopping = False

    def _on_signal(signum, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    sent = 0
    idx = 0
    try:
        while not stopping and (args.count == 0 or sent < args.count):
            sensor_id = sensor_ids[idx % len(sensor_ids)]
            idx += 1
            topic = f"sfdap/sensors/{sensor_id}"
            payload = random_payload()
            client.publish(topic, json.dumps(payload), qos=1)
            sent += 1
            print(f"[{sent}] {topic} → {payload}")
            time.sleep(args.interval)
    finally:
        client.loop_stop()
        client.disconnect()
        print(f"[mqtt_publisher] kapatiliyor (gonderilen mesaj: {sent})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
