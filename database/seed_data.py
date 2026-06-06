"""
SFDAP Demo Seed Data — Çiftçi-Odaklı Demo Veri Seti
====================================================
REBUILD pivot sonrası seed: "81 il / ulusal ölçek" iddiası bırakıldı.
Bunun yerine birkaç **demo çiftçi** + **admin/gözetmen** hesabıyla, onboarding
ve sunum demosu için yeterli küçük bir veri seti üretir.

Üretilen:
- 5 kullanıcı: admin, gözetmen (overseer) + 3 çiftçi (ahmet/ayşe/mehmet)
- 3 çiftlik (farklı bölgeler) · 6 tarla
- Tarla başına 1 sensör + ~15 diurnal toprak nemi okuması
- Çiftlik başına hava durumu kayıtları
- Sulama geçmişi, hastalık tanısı, toprak analizi, açık uyarı
- 17 bitki türü referansı (turkey_data.CROP_DATA)

Demo giriş bilgileri (script sonunda yazdırılır):
    Tüm demo hesapların şifresi: 123456
    admin@demo.test      (admin)
    overseer@demo.test   (overseer — sistem özeti)
    developer@demo.test  (developer — read-only + test)
    ahmet@demo.test      (farmer — ana persona)
    ayse@demo.test       (farmer)
    mehmet@demo.test     (farmer)

Kullanım:
    python database/seed_data.py
    # Sıfırdan: önce sfdap_dev.db dosyasını sil.
"""

import math
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
from loguru import logger

# Proje kök dizinini path'e ekle
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine
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
    User,
    WeatherData,
)
from app.routers.auth import _hash_password
from database.turkey_data import CROP_DATA

# ─── Demo kullanıcı + çiftlik tanımları ───────────────────────
# Tüm demo hesaplar tek basit şifre kullanır (yalnız yerel/demo — production değil).
DEMO_PASSWORD = "123456"  # noqa: S105 — demo seed, gerçek secret değil
FARMER_PASSWORD = DEMO_PASSWORD
ADMIN_PASSWORD = DEMO_PASSWORD
OVERSEER_PASSWORD = DEMO_PASSWORD
DEVELOPER_PASSWORD = DEMO_PASSWORD

# Her tarla: (ad, bitki_adı, toprak_tipi, alan_ha, taban_nem%) — taban_nem
# status'u belirler: <30 dry, 30-70 optimal, >70 wet.
DEMO_FARMS = [
    {
        "email": "ahmet@demo.test",
        "name": "Çiftçi Ahmet",
        "phone": "0532 000 0001",
        "farm_name": "Ahmet'in Çiftliği",
        "city": "Konya",
        "region": "İç Anadolu",
        "lat": 37.87,
        "lng": 32.48,
        "area": 8.0,
        "fields": [
            ("Tarla A", "Buğday", "killi", 3.5, 22.0),  # susuz (dry)
            ("Tarla B", "Domates", "tınlı", 2.0, 52.0),  # uygun (optimal)
        ],
    },
    {
        "email": "ayse@demo.test",
        "name": "Çiftçi Ayşe",
        "phone": "0532 000 0002",
        "farm_name": "Ayşe Bahçe",
        "city": "Antalya",
        "region": "Akdeniz",
        "lat": 36.88,
        "lng": 30.71,
        "area": 5.0,
        "fields": [
            ("Narenciye Bahçesi", "Narenciye", "kumlu-tınlı", 3.0, 48.0),
            ("Biber Serası", "Biber", "tınlı", 1.0, 60.0),
        ],
    },
    {
        "email": "mehmet@demo.test",
        "name": "Çiftçi Mehmet",
        "phone": "0532 000 0003",
        "farm_name": "Mehmet Tarım",
        "city": "Samsun",
        "region": "Karadeniz",
        "lat": 41.29,
        "lng": 36.33,
        "area": 6.5,
        "fields": [
            ("Fındık Bahçesi", "Fındık", "killi-tınlı", 4.0, 65.0),
            ("Mısır Tarlası", "Mısır", "tınlı", 2.5, 40.0),
        ],
    },
]


def _diurnal_factor(hour: int) -> float:
    """Günlük döngü faktörü: -1 (gece dip) ↔ +1 (öğle pik)."""
    return math.sin(2 * math.pi * (hour - 6) / 24)


def seed_database():
    """Veritabanını çiftçi-odaklı demo verilerle doldurur (idempotent)."""
    logger.info("🌱 SFDAP Çiftçi-Odaklı Demo Seed yükleniyor...")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        if db.query(User).count() > 0:
            logger.warning("⚠️  Veritabanında zaten veri var. Seed atlanıyor.")
            logger.warning("    Sıfırdan başlamak için sfdap_dev.db dosyasını silin.")
            return

        rng = np.random.default_rng(42)
        now = datetime.now(UTC)

        # ─── 1. BİTKİ TÜRLERİ (referans, 17 bitki) ───────────────────
        logger.info("  🌾 17 bitki türü oluşturuluyor...")
        crop_by_name: dict[str, CropType] = {}
        for name, sci, ph_min, ph_max, t_min, t_max, water, days in CROP_DATA:
            crop = CropType(
                name=name,
                scientific_name=sci,
                optimal_ph_min=ph_min,
                optimal_ph_max=ph_max,
                optimal_temp_min=t_min,
                optimal_temp_max=t_max,
                water_need_mm_per_day=water,
                growth_duration_days=days,
            )
            db.add(crop)
            crop_by_name[name] = crop
        db.flush()

        # ─── 2. KULLANICILAR (admin + gözetmen + geliştirici) ────────
        logger.info("  👤 Kullanıcılar oluşturuluyor (admin + gözetmen + geliştirici + 3 çiftçi)...")
        db.add(
            User(
                name="Yönetici Demo",
                email="admin@demo.test",
                password_hash=_hash_password(ADMIN_PASSWORD),
                role="admin",
            )
        )
        db.add(
            User(
                name="Gözetmen Demo",
                email="overseer@demo.test",
                password_hash=_hash_password(OVERSEER_PASSWORD),
                role="overseer",
            )
        )
        db.add(
            User(
                name="Geliştirici Demo",
                email="developer@demo.test",
                password_hash=_hash_password(DEVELOPER_PASSWORD),
                role="developer",
            )
        )

        # ─── 3. ÇİFTÇİLER + ÇİFTLİK/TARLA/SENSÖR ZİNCİRİ ─────────────
        total_fields = total_sensors = total_readings = 0
        for spec in DEMO_FARMS:
            farmer = User(
                name=spec["name"],
                email=spec["email"],
                password_hash=_hash_password(FARMER_PASSWORD),
                role="farmer",
                phone=spec["phone"],
            )
            db.add(farmer)
            db.flush()

            farm = Farm(
                user_id=farmer.id,
                name=spec["farm_name"],
                city=spec["city"],
                region=spec["region"],
                location_lat=spec["lat"],
                location_lng=spec["lng"],
                area_hectares=spec["area"],
            )
            db.add(farm)
            db.flush()

            # Çiftlik başına birkaç hava durumu kaydı (son 5 gün)
            for d in range(5):
                db.add(
                    WeatherData(
                        farm_id=farm.id,
                        recorded_at=now - timedelta(days=d),
                        temperature_c=round(float(rng.uniform(14, 30)), 1),
                        humidity_percent=round(float(rng.uniform(40, 80)), 1),
                        precipitation_mm=round(float(rng.uniform(0, 8)), 1),
                        wind_speed_kmh=round(float(rng.uniform(3, 25)), 1),
                    )
                )

            for fname, crop_name, soil, area, base_moisture in spec["fields"]:
                crop = crop_by_name.get(crop_name)
                field = Field(
                    farm_id=farm.id,
                    name=fname,
                    soil_type=soil,
                    area_hectares=area,
                    elevation_m=round(float(rng.uniform(50, 1100)), 0),
                    crop_id=crop.id if crop else None,
                )
                db.add(field)
                db.flush()
                total_fields += 1

                sensor = Sensor(
                    field_id=field.id,
                    sensor_type="soil_moisture",
                    serial_number=f"SN-{farm.id}-{field.id}",
                    installation_date=now - timedelta(days=120),
                    depth_cm=20.0,
                    lat=spec["lat"],
                    lng=spec["lng"],
                    status="active",
                )
                db.add(sensor)
                db.flush()
                total_sensors += 1

                # ~15 diurnal okuma (son ~30 saat, 2 saatte bir)
                for h in range(0, 30, 2):
                    moisture = base_moisture + _diurnal_factor((now.hour - h) % 24) * 4 + float(rng.normal(0, 1.5))
                    db.add(
                        SoilMoistureReading(
                            sensor_id=sensor.id,
                            reading_timestamp=now - timedelta(hours=h),
                            moisture_percent=round(max(0.0, min(100.0, moisture)), 1),
                            soil_temperature_c=round(float(rng.uniform(14, 22)), 1),
                            depth_cm=20.0,
                        )
                    )
                    total_readings += 1

                # Sulama geçmişi (son 2 kayıt)
                db.add(
                    IrrigationSchedule(
                        field_id=field.id,
                        scheduled_date=now - timedelta(days=1),
                        water_amount_liters=round(float(rng.uniform(150, 350)), 0),
                        duration_min=int(rng.integers(30, 60)),
                        status="completed",
                        source="model",
                    )
                )

                # Toprak analizi (her tarlaya 1)
                db.add(
                    SoilAnalysis(
                        field_id=field.id,
                        analysis_date=now - timedelta(days=int(rng.integers(5, 30))),
                        ph_level=round(float(rng.uniform(6.0, 7.5)), 1),
                        nitrogen_mg_kg=round(float(rng.uniform(30, 60)), 0),
                        phosphorus_mg_kg=round(float(rng.uniform(15, 35)), 0),
                        potassium_mg_kg=round(float(rng.uniform(120, 200)), 0),
                        texture_class=soil,
                    )
                )

            # Ahmet'in Tarla A'sı için demo hastalık + kritik uyarı (susuz)
            if spec["email"] == "ahmet@demo.test":
                tarla_a = db.query(Field).filter(Field.farm_id == farm.id, Field.name == "Tarla A").first()
                db.add(
                    PlantHealthImage(
                        field_id=tarla_a.id,
                        image_url="/static/plant_uploads/demo_leaf.jpg",
                        captured_at=now - timedelta(hours=6),
                        diagnosis="leaf_rust",
                        confidence_score=0.84,
                        severity="moderate",
                    )
                )
                db.add(
                    SystemAlert(
                        farm_id=farm.id,
                        field_id=tarla_a.id,
                        alert_type="sensor_anomaly",
                        severity="critical",
                        message="Tarla A toprak nemi kritik düşük — sulama önerilir.",
                        is_resolved=False,
                    )
                )

        db.commit()

        # ─── Özet ────────────────────────────────────────────────────
        logger.info("✅ Demo seed tamamlandı:")
        logger.info(f"   👤 {db.query(User).count()} kullanıcı (admin + gözetmen + geliştirici + 3 çiftçi)")
        logger.info(f"   🚜 {db.query(Farm).count()} çiftlik · 🌱 {total_fields} tarla")
        logger.info(f"   📡 {total_sensors} sensör · 📊 {total_readings} okuma")
        logger.info("   🔑 Giriş: tüm demo hesaplar şifre '123456' (ör. ahmet@demo.test çiftçi, admin@demo.test admin)")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
