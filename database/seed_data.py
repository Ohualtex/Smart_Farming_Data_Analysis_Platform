"""
SFDAP Demo Seed Data — 81 İl Kapsamlı Veri Seti
==================================================
Türkiye'nin 81 ili için gerçekçi tarım verileri:
- 81 çiftlik (her ile 1)
- 15 bitki türü
- 162 tarla (her çiftlikte 2)
- 324 sensör, ~4800 sensör okuması
- ~1200 hava durumu kaydı
- ~320 sulama programı
- 162 toprak analizi, 162 ekim kaydı, 162 gübre önerisi
- Sistem uyarıları ve model performans logları

Emirhan Günay & Miraç Duran — Cycle 6

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
    CropPlanting,
    CropType,
    Farm,
    FertilizerRecommendationLog,
    Field,
    IrrigationSchedule,
    ModelPerformanceLog,
    Sensor,
    SoilAnalysis,
    SoilMoistureReading,
    SystemAlert,
    User,
    WeatherData,
)
from database.turkey_data import CROP_DATA, PROVINCES, REGION_CROPS, SOIL_TYPES


def seed_database():
    """Veritabanını 81 il kapsamlı demo verilerle doldurur."""
    print("🌱 SFDAP 81 İl Seed Data yükleniyor...")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
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
                password_hash="hashed_pw_1",
                role="farmer",
                phone="05321234567",
            ),
            User(
                name="Fatma Demir",
                email="fatma@sfdap.com",
                password_hash="hashed_pw_2",
                role="farmer",
                phone="05339876543",
            ),
            User(
                name="Miraç Duran",
                email="mirac@sfdap.com",
                password_hash="hashed_pw_3",
                role="admin",
                phone="05551112233",
            ),
            User(
                name="Emirhan Günay",
                email="emirhan@sfdap.com",
                password_hash="hashed_pw_4",
                role="farmer",
                phone="05441112233",
            ),
            User(
                name="Ecenur Üner",
                email="ecenur@sfdap.com",
                password_hash="hashed_pw_5",
                role="farmer",
                phone="05361112233",
            ),
        ]
        db.add_all(users)
        db.flush()

        # ─── 2. BİTKİ TÜRLERİ (15 adet) ─────────────────────────────
        print("  🌿 15 bitki türü oluşturuluyor...")
        crop_types = []
        for name, sci, ph_min, ph_max, t_min, t_max, water, days in CROP_DATA:
            crop_types.append(
                CropType(
                    name=name,
                    scientific_name=sci,
                    optimal_ph_min=ph_min,
                    optimal_ph_max=ph_max,
                    optimal_temp_min=float(t_min),
                    optimal_temp_max=float(t_max),
                    water_need_mm_per_day=water,
                    growth_duration_days=days,
                )
            )
        db.add_all(crop_types)
        db.flush()

        # ─── 3. ÇİFTLİKLER (81 il) & TARLALAR (162) ─────────────────
        print("  🏡 81 il çiftliği ve 162 tarla oluşturuluyor...")
        all_farms = []
        all_fields = []

        for idx, (city, lat, lng, region, _base_temp, _base_hum) in enumerate(PROVINCES):
            user = users[idx % len(users)]
            farm = Farm(
                user_id=user.id,
                name=f"{city} Tarım Çiftliği",
                location_lat=lat,
                location_lng=lng,
                area_hectares=round(float(rng.uniform(30, 300)), 1),
                city=city,
                region=region,
            )
            all_farms.append(farm)

        db.add_all(all_farms)
        db.flush()

        for idx, farm in enumerate(all_farms):
            region = PROVINCES[idx][3]
            crop_indices = REGION_CROPS[region]
            soil = rng.choice(SOIL_TYPES)

            for j in range(2):
                ci = crop_indices[j % len(crop_indices)]
                field = Field(
                    farm_id=farm.id,
                    name=f"{crop_types[ci].name} Tarlası {j + 1}",
                    area_hectares=round(float(rng.uniform(10, 80)), 1),
                    soil_type=soil if j == 0 else rng.choice(SOIL_TYPES),
                    elevation_m=round(float(rng.uniform(5, 1800)), 0),
                    crop_id=crop_types[ci].id,
                )
                all_fields.append(field)

        db.add_all(all_fields)
        db.flush()

        # ─── 4. SENSÖRLER (324) ──────────────────────────────────────
        print("  📡 324 sensör oluşturuluyor...")
        all_sensors = []
        for i, field in enumerate(all_fields):
            for st_idx, stype in enumerate(["soil_moisture", "soil_temperature"]):
                s = Sensor(
                    field_id=field.id,
                    sensor_type=stype,
                    serial_number=f"SN-{i:04d}-{st_idx}",
                    installation_date=now - timedelta(days=int(rng.integers(30, 365))),
                    depth_cm=round(float(rng.uniform(10, 30)), 0),
                    status="active",
                )
                all_sensors.append(s)
        db.add_all(all_sensors)
        db.flush()

        # ─── 5. SENSÖR OKUMALARI (~4800) ──────────────────────────────
        print("  📊 Sensör okumaları oluşturuluyor...")
        readings = []
        for sensor in all_sensors:
            for day in range(15):
                ts = now - timedelta(days=day, hours=int(rng.integers(0, 12)))
                readings.append(
                    SoilMoistureReading(
                        sensor_id=sensor.id,
                        reading_timestamp=ts,
                        moisture_percent=round(float(rng.uniform(20, 80)), 1),
                        depth_cm=sensor.depth_cm,
                        soil_temperature_c=round(float(rng.uniform(8, 32)), 1),
                        electrical_conductivity=round(float(rng.uniform(0.3, 3.5)), 2),
                    )
                )
        db.add_all(readings)
        db.flush()
        print(f"    → {len(readings)} okuma oluşturuldu")

        # ─── 6. HAVA DURUMU (~1200) ──────────────────────────────────
        print("  🌤️ Hava durumu verileri oluşturuluyor...")
        weather = []
        for idx, farm in enumerate(all_farms):
            base_temp = PROVINCES[idx][4]
            base_hum = PROVINCES[idx][5]
            for day in range(15):
                ts = now - timedelta(days=day, hours=int(rng.integers(6, 18)))
                weather.append(
                    WeatherData(
                        farm_id=farm.id,
                        recorded_at=ts,
                        temperature_c=round(base_temp + float(rng.uniform(-6, 8)), 1),
                        humidity_percent=round(base_hum + float(rng.uniform(-15, 20)), 1),
                        precipitation_mm=round(float(rng.choice([0, 0, 0, 0, rng.uniform(0.5, 15)])), 1),
                        wind_speed_kmh=round(float(rng.uniform(2, 35)), 1),
                        solar_radiation=round(float(rng.uniform(150, 900)), 1),
                        uv_index=round(float(rng.uniform(1, 11)), 1),
                    )
                )
        db.add_all(weather)
        db.flush()
        print(f"    → {len(weather)} hava durumu kaydı oluşturuldu")

        # ─── 7. SULAMA PROGRAMLARI (~320) ─────────────────────────────
        print("  💧 Sulama programları oluşturuluyor...")
        irrigations = []
        statuses = ["completed", "completed", "completed", "pending", "cancelled"]
        for field in all_fields:
            for _ in range(2):
                irrigations.append(
                    IrrigationSchedule(
                        field_id=field.id,
                        scheduled_date=now - timedelta(days=int(rng.integers(1, 25))),
                        duration_min=int(rng.integers(30, 120)),
                        water_amount_liters=round(float(rng.uniform(500, 5000)), 0),
                        source=rng.choice(["model", "manual"]),
                        status=rng.choice(statuses),
                    )
                )
        db.add_all(irrigations)
        db.flush()
        print(f"    → {len(irrigations)} sulama programı oluşturuldu")

        # ─── 8. TOPRAK ANALİZLERİ (162) ──────────────────────────────
        print("  🧪 Toprak analizleri oluşturuluyor...")
        soil_analyses = []
        for field in all_fields:
            soil_analyses.append(
                SoilAnalysis(
                    field_id=field.id,
                    analysis_date=now - timedelta(days=int(rng.integers(10, 90))),
                    ph_level=round(float(rng.uniform(5.0, 8.5)), 1),
                    organic_matter_pct=round(float(rng.uniform(1.0, 5.0)), 1),
                    nitrogen_mg_kg=round(float(rng.uniform(5, 80)), 1),
                    phosphorus_mg_kg=round(float(rng.uniform(3, 50)), 1),
                    potassium_mg_kg=round(float(rng.uniform(50, 300)), 1),
                    calcium_mg_kg=round(float(rng.uniform(500, 5000)), 0),
                    magnesium_mg_kg=round(float(rng.uniform(50, 500)), 0),
                    texture_class=field.soil_type,
                    notes=f"{field.name} tarlası için lab analiz sonuçları.",
                )
            )
        db.add_all(soil_analyses)
        db.flush()
        print(f"    → {len(soil_analyses)} toprak analizi oluşturuldu")

        # ─── 9. EKİM TAKİBİ (162) ────────────────────────────────────
        print("  🌾 Ekim kayıtları oluşturuluyor...")
        plantings = []
        for field in all_fields:
            plant_date = now - timedelta(days=int(rng.integers(30, 120)))
            duration = crop_types[0].growth_duration_days or 90
            if field.crop_id:
                for ct in crop_types:
                    if ct.id == field.crop_id:
                        duration = ct.growth_duration_days or 90
                        break
            plantings.append(
                CropPlanting(
                    field_id=field.id,
                    crop_id=field.crop_id or crop_types[0].id,
                    planting_date=plant_date,
                    expected_harvest_date=plant_date + timedelta(days=duration),
                    season="2025-2026",
                    status=rng.choice(["growing", "growing", "harvested"]),
                )
            )
        db.add_all(plantings)
        db.flush()
        print(f"    → {len(plantings)} ekim kaydı oluşturuldu")

        # ─── 10. GÜBRE ÖNERİLERİ (162) ───────────────────────────────
        print("  🧬 Gübre önerileri oluşturuluyor...")
        fert_recs = []
        for field in all_fields:
            n = round(float(rng.uniform(10, 60)), 1)
            p = round(float(rng.uniform(5, 30)), 1)
            k = round(float(rng.uniform(10, 50)), 1)
            fert_recs.append(
                FertilizerRecommendationLog(
                    field_id=field.id,
                    crop_id=field.crop_id or crop_types[0].id,
                    recommended_at=now - timedelta(days=int(rng.integers(5, 30))),
                    nitrogen_kg=n,
                    phosphorus_kg=p,
                    potassium_kg=k,
                    total_fertilizer_kg=round(n + p + k, 1),
                    recommendation_text=f"NPK {n:.0f}-{p:.0f}-{k:.0f} uygulanması önerilir.",
                    is_applied=bool(rng.choice([True, False])),
                )
            )
        db.add_all(fert_recs)
        db.flush()
        print(f"    → {len(fert_recs)} gübre önerisi oluşturuldu")

        # ─── 11. SİSTEM UYARILARI & MODEL LOGLAR ─────────────────────
        print("  🚨 Sistem uyarıları ve model logları oluşturuluyor...")
        alerts = []
        alert_templates = [
            ("sensor_anomaly", "medium", "Sensör okumalarında anomali tespit edildi."),
            ("weather_warning", "critical", "Şiddetli yağış uyarısı."),
            ("system_error", "low", "Sensör bağlantısı geçici olarak kesildi."),
        ]
        for i in range(30):
            farm = all_farms[i % len(all_farms)]
            atype, sev, msg = alert_templates[i % 3]
            alerts.append(
                SystemAlert(
                    farm_id=farm.id,
                    field_id=all_fields[i * 2 % len(all_fields)].id if i % 2 == 0 else None,
                    alert_type=atype,
                    severity=sev,
                    message=f"{farm.city}: {msg}",
                    is_resolved=bool(rng.choice([True, False])),
                    created_at=now - timedelta(hours=int(rng.integers(1, 720))),
                )
            )
        db.add_all(alerts)

        perf_logs = []
        for _i in range(20):
            perf_logs.append(
                ModelPerformanceLog(
                    model_name=rng.choice(["irrigation_rf", "plant_disease_cnn"]),
                    prediction_data=f'{{"prediction": {round(float(rng.uniform(0.5, 1.0)), 2)}}}',
                    actual_data=f'{{"actual": {round(float(rng.uniform(0.5, 1.0)), 2)}}}',
                    accuracy_score=round(float(rng.uniform(0.75, 1.0)), 3),
                    logged_at=now - timedelta(days=int(rng.integers(1, 30))),
                )
            )
        db.add_all(perf_logs)
        db.flush()

        # ─── COMMIT ──────────────────────────────────────────────────
        db.commit()

        # ─── ÖZET ────────────────────────────────────────────────────
        total = (
            len(users)
            + len(crop_types)
            + len(all_farms)
            + len(all_fields)
            + len(all_sensors)
            + len(readings)
            + len(weather)
            + len(irrigations)
            + len(soil_analyses)
            + len(plantings)
            + len(fert_recs)
            + len(alerts)
            + len(perf_logs)
        )
        print(f"\n✅ Seed data başarıyla yüklendi! (Toplam: {total} kayıt)")
        print(f"   👤 {len(users)} kullanıcı")
        print(f"   🌿 {len(crop_types)} bitki türü")
        print(f"   🏡 {len(all_farms)} çiftlik (81 il)")
        print(f"   🌾 {len(all_fields)} tarla")
        print(f"   📡 {len(all_sensors)} sensör")
        print(f"   📊 {len(readings)} sensör okuması")
        print(f"   🌤️ {len(weather)} hava durumu kaydı")
        print(f"   💧 {len(irrigations)} sulama programı")
        print(f"   🧪 {len(soil_analyses)} toprak analizi")
        print(f"   🌾 {len(plantings)} ekim kaydı")
        print(f"   🧬 {len(fert_recs)} gübre önerisi")
        print(f"   🚨 {len(alerts)} sistem uyarısı")
        print(f"   📈 {len(perf_logs)} performans logu")

    except Exception as e:
        db.rollback()
        print(f"❌ Hata: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
