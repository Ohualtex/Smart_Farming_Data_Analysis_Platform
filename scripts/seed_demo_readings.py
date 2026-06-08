"""Demo hazırlık — mevcut sensörlere son 48 saatlik TAZE toprak nemi okuması ekler.

Neden gerekli: dashboard 'son 24 saat' penceresi kullanır; seed okumaları zamanla
eskir (>24h) ve 'Veri yok' görünür. Bu script demo ÖNCESİ çalıştırılır.
Idempotent: her sensör için son 48h yeniden yazılır (dup birikmez).

Kullanım:  PYTHONPATH=. .venv/bin/python scripts/seed_demo_readings.py
"""

import math
from datetime import UTC, datetime, timedelta

from app.database import SessionLocal
from app.models.models import Sensor, SoilMoistureReading

HOURS = 48


def seed_readings() -> None:
    db = SessionLocal()
    try:
        sensors = db.query(Sensor).all()
        if not sensors:
            print("⚠️  Sensör yok — önce seed_data.py çalıştır.")
            return
        now = datetime.now(UTC)
        cutoff = now - timedelta(hours=HOURS)
        added = 0
        for i, sensor in enumerate(sensors):
            # idempotent: son 48h'ı temizle, yeniden yaz
            db.query(SoilMoistureReading).filter(
                SoilMoistureReading.sensor_id == sensor.id,
                SoilMoistureReading.reading_timestamp >= cutoff,
            ).delete(synchronize_session=False)
            base = 45.0 + (i % 5) * 3.0  # sensöre göre 45-57 taban nem
            for h in range(HOURS):
                ts = now - timedelta(hours=h)
                diurnal = 8.0 * math.sin((ts.hour / 24) * 2 * math.pi)  # gün/gece dalgası
                noise = (h * 7) % 5 - 2  # -2..+2 deterministik
                moisture = max(15.0, min(90.0, base + diurnal + noise))
                temp = 18.0 + 5.0 * math.sin(((ts.hour - 4) / 24) * 2 * math.pi)
                db.add(
                    SoilMoistureReading(
                        sensor_id=sensor.id,
                        reading_timestamp=ts,
                        moisture_percent=round(moisture, 1),
                        soil_temperature_c=round(temp, 1),
                    )
                )
                added += 1
        db.commit()
        print(f"✓ {len(sensors)} sensör × {HOURS}h = {added} taze okuma eklendi (son {HOURS}h, idempotent).")
    finally:
        db.close()


if __name__ == "__main__":
    seed_readings()
