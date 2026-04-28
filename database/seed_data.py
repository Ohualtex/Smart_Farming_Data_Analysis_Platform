"""
SFDAP Demo Seed Data
======================
Sunumda gösterilebilecek gerçekçi demo verileri:
- 3 çiftlik (Adana, Konya, İzmir)
- 5 tarla
- 10 sensör
- 100+ sensör okuması (30 günlük)
- 90+ hava durumu kaydı (30 günlük)
- 20 sulama programı

Emirhan Günay — Cycle 5 Görevi

Kullanım:
    python database/seed_data.py
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

# Proje kök dizinini path'e ekle
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine
from app.models.models import (
    CropType,
    Farm,
    Field,
    IrrigationSchedule,
    Sensor,
    SoilMoistureReading,
    User,
    WeatherData,
)


def seed_database():
    """Veritabanını demo verilerle doldurur."""
    print("🌱 SFDAP Seed Data yükleniyor...")

    # Tabloları oluştur
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Mevcut verileri kontrol et
        if db.query(User).count() > 0:
            print("⚠️  Veritabanında zaten veri var. Seed atlanıyor.")
            print("    Sıfırdan başlamak için sfdap_dev.db dosyasını silin.")
            return

        rng = np.random.default_rng(42)
        now = datetime.now(timezone.utc)

        # ─── 1. KULLANICILAR ─────────────────────────────────────────
        print("  👤 Kullanıcılar oluşturuluyor...")
        users = [
            User(
                name="Ahmet Yılmaz",
                email="ahmet@sfdap.com",
                password_hash="hashed_demo_pw_1",
                role="farmer",
                phone="05321234567",
            ),
            User(
                name="Fatma Demir",
                email="fatma@sfdap.com",
                password_hash="hashed_demo_pw_2",
                role="farmer",
                phone="05339876543",
            ),
            User(
                name="Miraç Duran",
                email="mirac@sfdap.com",
                password_hash="hashed_demo_pw_3",
                role="admin",
                phone="05551112233",
            ),
        ]
        db.add_all(users)
        db.flush()

        # ─── 2. ÇİFTLİKLER ──────────────────────────────────────────
        print("  🏡 Çiftlikler oluşturuluyor...")
        farms = [
            Farm(
                user_id=users[0].id,
                name="Adana Ovası Çiftliği",
                location_lat=36.9914,
                location_lng=35.3308,
                area_hectares=120.0,
                city="Adana",
                region="Akdeniz",
            ),
            Farm(
                user_id=users[1].id,
                name="Konya Karapınar Tarım",
                location_lat=37.7167,
                location_lng=33.5500,
                area_hectares=250.0,
                city="Konya",
                region="İç Anadolu",
            ),
            Farm(
                user_id=users[2].id,
                name="İzmir Ödemiş Zeytinliği",
                location_lat=38.2292,
                location_lng=27.9714,
                area_hectares=45.0,
                city="İzmir",
                region="Ege",
            ),
        ]
        db.add_all(farms)
        db.flush()

        # ─── 3. TARLALAR ─────────────────────────────────────────────
        print("  🌾 Tarlalar oluşturuluyor...")
        fields = [
            Field(
                farm_id=farms[0].id,
                name="Buğday Tarlası A",
                area_hectares=40.0,
                soil_type="killi-tınlı",
                elevation_m=30.0,
            ),
            Field(
                farm_id=farms[0].id,
                name="Pamuk Tarlası B",
                area_hectares=35.0,
                soil_type="kumlu-tınlı",
                elevation_m=28.0,
            ),
            Field(
                farm_id=farms[1].id,
                name="Mısır Tarlası",
                area_hectares=80.0,
                soil_type="tınlı",
                elevation_m=1020.0,
            ),
            Field(
                farm_id=farms[1].id,
                name="Ayçiçeği Bölgesi",
                area_hectares=60.0,
                soil_type="killi",
                elevation_m=1015.0,
            ),
            Field(
                farm_id=farms[2].id,
                name="Zeytin Bahçesi",
                area_hectares=25.0,
                soil_type="kumlu",
                elevation_m=180.0,
            ),
        ]
        db.add_all(fields)
        db.flush()

        # ─── 4. BİTKİ TÜRLERİ ────────────────────────────────────────
        print("  🌿 Bitki türleri oluşturuluyor...")
        crop_types = [
            CropType(
                name="Buğday",
                scientific_name="Triticum aestivum",
                optimal_ph_min=6.0,
                optimal_ph_max=7.5,
                optimal_temp_min=12.0,
                optimal_temp_max=25.0,
                water_need_mm_per_day=5.0,
                growth_duration_days=120,
            ),
            CropType(
                name="Mısır",
                scientific_name="Zea mays",
                optimal_ph_min=5.8,
                optimal_ph_max=7.0,
                optimal_temp_min=18.0,
                optimal_temp_max=33.0,
                water_need_mm_per_day=7.0,
                growth_duration_days=90,
            ),
            CropType(
                name="Domates",
                scientific_name="Solanum lycopersicum",
                optimal_ph_min=6.0,
                optimal_ph_max=6.8,
                optimal_temp_min=20.0,
                optimal_temp_max=30.0,
                water_need_mm_per_day=6.0,
                growth_duration_days=75,
            ),
        ]
        db.add_all(crop_types)
        db.flush()

        # ─── 5. SENSÖRLER ────────────────────────────────────────────
        print("  📡 Sensörler oluşturuluyor...")
        sensor_configs = [
            (fields[0].id, "soil_moisture", "SM-ADA-001", 15.0),
            (fields[0].id, "soil_moisture", "SM-ADA-002", 30.0),
            (fields[0].id, "soil_temperature", "ST-ADA-001", 10.0),
            (fields[1].id, "soil_moisture", "SM-ADA-003", 20.0),
            (fields[1].id, "electrical_conductivity", "EC-ADA-001", 15.0),
            (fields[2].id, "soil_moisture", "SM-KON-001", 20.0),
            (fields[2].id, "soil_temperature", "ST-KON-001", 15.0),
            (fields[3].id, "soil_moisture", "SM-KON-002", 25.0),
            (fields[4].id, "soil_moisture", "SM-IZM-001", 15.0),
            (fields[4].id, "soil_temperature", "ST-IZM-001", 10.0),
        ]

        sensors = []
        for field_id, stype, serial, depth in sensor_configs:
            s = Sensor(
                field_id=field_id,
                sensor_type=stype,
                serial_number=serial,
                installation_date=now - timedelta(days=90),
                depth_cm=depth,
                status="active",
            )
            sensors.append(s)
        db.add_all(sensors)
        db.flush()

        # ─── 6. SENSÖR OKUMALARI (100+ kayıt) ────────────────────────
        print("  📊 Sensör okumaları oluşturuluyor (100+ kayıt)...")
        readings = []
        for sensor in sensors:
            # Her sensör için son 30 günde günde 1-2 okuma
            for day_offset in range(30):
                timestamp = now - timedelta(days=day_offset, hours=int(rng.integers(0, 12)))

                if sensor.sensor_type == "soil_moisture":
                    moisture = round(float(rng.uniform(25, 75)), 1)
                    temp = round(float(rng.uniform(12, 28)), 1)
                elif sensor.sensor_type == "soil_temperature":
                    moisture = round(float(rng.uniform(30, 60)), 1)
                    temp = round(float(rng.uniform(10, 35)), 1)
                else:  # EC
                    moisture = round(float(rng.uniform(35, 55)), 1)
                    temp = round(float(rng.uniform(15, 25)), 1)

                readings.append(
                    SoilMoistureReading(
                        sensor_id=sensor.id,
                        reading_timestamp=timestamp,
                        moisture_percent=moisture,
                        depth_cm=sensor.depth_cm,
                        soil_temperature_c=temp,
                        electrical_conductivity=round(float(rng.uniform(0.5, 3.0)), 2),
                    )
                )
        db.add_all(readings)
        db.flush()
        print(f"    → {len(readings)} okuma oluşturuldu")

        # ─── 7. HAVA DURUMU VERİLERİ (90+ kayıt) ─────────────────────
        print("  🌤️ Hava durumu verileri oluşturuluyor...")
        weather_records = []
        for farm in farms:
            for day_offset in range(30):
                timestamp = now - timedelta(days=day_offset, hours=int(rng.integers(6, 18)))

                # Bölgeye göre sıcaklık ve nem ayarla
                if farm.city == "Adana":
                    base_temp, base_humidity = 22.0, 65.0
                elif farm.city == "Konya":
                    base_temp, base_humidity = 15.0, 45.0
                else:  # İzmir
                    base_temp, base_humidity = 20.0, 55.0

                weather_records.append(
                    WeatherData(
                        farm_id=farm.id,
                        recorded_at=timestamp,
                        temperature_c=round(base_temp + float(rng.uniform(-5, 8)), 1),
                        humidity_percent=round(base_humidity + float(rng.uniform(-15, 20)), 1),
                        precipitation_mm=round(float(rng.choice([0, 0, 0, 0, rng.uniform(0.5, 15)])), 1),
                        wind_speed_kmh=round(float(rng.uniform(2, 35)), 1),
                        solar_radiation=round(float(rng.uniform(200, 900)), 1),
                        uv_index=round(float(rng.uniform(2, 10)), 1),
                    )
                )
        db.add_all(weather_records)
        db.flush()
        print(f"    → {len(weather_records)} hava durumu kaydı oluşturuldu")

        # ─── 8. SULAMA PROGRAMLARI (20 kayıt) ────────────────────────
        print("  💧 Sulama programları oluşturuluyor...")
        irrigation_records = []
        statuses = ["completed", "completed", "completed", "pending", "cancelled"]
        for field in fields:
            for _i in range(4):
                scheduled = now - timedelta(days=int(rng.integers(1, 25)))
                irrigation_records.append(
                    IrrigationSchedule(
                        field_id=field.id,
                        scheduled_date=scheduled,
                        duration_min=int(rng.integers(30, 120)),
                        water_amount_liters=round(float(rng.uniform(500, 5000)), 0),
                        source=rng.choice(["model", "manual"]),
                        status=rng.choice(statuses),
                    )
                )
        db.add_all(irrigation_records)
        db.flush()
        print(f"    → {len(irrigation_records)} sulama programı oluşturuldu")

        # ─── COMMIT ──────────────────────────────────────────────────
        db.commit()

        # ─── ÖZET ────────────────────────────────────────────────────
        print("\n✅ Seed data başarıyla yüklendi!")
        print(f"   👤 {len(users)} kullanıcı")
        print(f"   🏡 {len(farms)} çiftlik")
        print(f"   🌾 {len(fields)} tarla")
        print(f"   🌿 {len(crop_types)} bitki türü")
        print(f"   📡 {len(sensors)} sensör")
        print(f"   📊 {len(readings)} sensör okuması")
        print(f"   🌤️ {len(weather_records)} hava durumu kaydı")
        print(f"   💧 {len(irrigation_records)} sulama programı")

    except Exception as e:
        db.rollback()
        print(f"❌ Hata: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
