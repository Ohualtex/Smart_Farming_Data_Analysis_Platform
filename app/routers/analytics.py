"""
Analytics API Endpoint'leri
=============================
Veri görselleştirme panosu için toplu istatistik ve
içgörü verileri döndüren endpoint'ler.

Miraç Duran — Cycle 6 Görevi
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import (
    Farm,
    Field,
    IrrigationSchedule,
    Sensor,
    SoilMoistureReading,
    User,
    WeatherData,
)

router = APIRouter(prefix="/api/analytics", tags=["Analitik & Görselleştirme"])


@router.get("/summary")
def get_analytics_summary(
    days: int = Query(default=30, ge=1, le=365, description="Son kaç gün"),
    db: Session = Depends(get_db),
):
    """
    Dashboard analitik panosu için toplu istatistik verileri döndürür.

    İçerikler:
    - Genel sayaçlar (çiftlik, tarla, sensör, okuma, hava durumu kaydı)
    - Sensör tipi dağılımı (doughnut chart için)
    - Çiftlik bazlı hava durumu karşılaştırması
    - Sulama durumu dağılımı (polar area chart için)
    - NPK bitki profilleri (radar chart için)
    - Günlük sıcaklık & nem trendleri (ısı haritası için)
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # ─── GENEL SAYAÇLAR ──────────────────────────────────────────
    counts = {
        "users": db.query(func.count(User.id)).scalar() or 0,
        "farms": db.query(func.count(Farm.id)).scalar() or 0,
        "fields": db.query(func.count(Field.id)).scalar() or 0,
        "sensors": db.query(func.count(Sensor.id)).scalar() or 0,
        "readings": db.query(func.count(SoilMoistureReading.id)).scalar() or 0,
        "weather_records": db.query(func.count(WeatherData.id)).scalar() or 0,
        "irrigation_schedules": db.query(func.count(IrrigationSchedule.id)).scalar() or 0,
    }

    # ─── SENSÖR TİPİ DAĞILIMI ────────────────────────────────────
    sensor_types_raw = db.query(Sensor.sensor_type, func.count(Sensor.id)).group_by(Sensor.sensor_type).all()
    sensor_type_distribution = [{"type": row[0], "count": row[1]} for row in sensor_types_raw]

    # ─── ÇİFTLİK BAZLI HAVA DURUMU KARŞILAŞTIRMASI ───────────────
    farms = db.query(Farm).all()
    farm_weather_comparison = []

    for farm in farms:
        weather_records = (
            db.query(WeatherData).filter(WeatherData.farm_id == farm.id, WeatherData.recorded_at >= since).all()
        )

        if not weather_records:
            continue

        temps = [r.temperature_c for r in weather_records if r.temperature_c is not None]
        hums = [r.humidity_percent for r in weather_records if r.humidity_percent is not None]
        precips = [r.precipitation_mm for r in weather_records if r.precipitation_mm is not None]

        farm_weather_comparison.append(
            {
                "farm_id": farm.id,
                "farm_name": farm.name,
                "city": farm.city,
                "temperature": {
                    "avg": round(sum(temps) / len(temps), 1) if temps else None,
                    "min": round(min(temps), 1) if temps else None,
                    "max": round(max(temps), 1) if temps else None,
                },
                "humidity": {
                    "avg": round(sum(hums) / len(hums), 1) if hums else None,
                    "min": round(min(hums), 1) if hums else None,
                    "max": round(max(hums), 1) if hums else None,
                },
                "precipitation_total_mm": round(sum(precips), 1) if precips else 0,
                "record_count": len(weather_records),
            }
        )

    # ─── SULAMA DURUMU DAĞILIMI ───────────────────────────────────
    irrigation_status_raw = (
        db.query(IrrigationSchedule.status, func.count(IrrigationSchedule.id)).group_by(IrrigationSchedule.status).all()
    )
    irrigation_status_distribution = [{"status": row[0], "count": row[1]} for row in irrigation_status_raw]

    # ─── GÜNLÜK SICAKLIK TRENDİ (ÇİFTLİK BAZLI) ──────────────────
    daily_trends = []
    for farm in farms:
        records = (
            db.query(WeatherData)
            .filter(WeatherData.farm_id == farm.id, WeatherData.recorded_at >= since)
            .order_by(WeatherData.recorded_at)
            .all()
        )

        if not records:
            continue

        # Günlük grupla
        day_groups: dict[str, list] = {}
        for r in records:
            if r.recorded_at:
                day_key = r.recorded_at.strftime("%Y-%m-%d")
                if day_key not in day_groups:
                    day_groups[day_key] = []
                day_groups[day_key].append(r)

        farm_trend = {
            "farm_id": farm.id,
            "farm_name": farm.name,
            "city": farm.city,
            "days": [],
        }

        for day_key in sorted(day_groups.keys()):
            day_records = day_groups[day_key]
            temps = [r.temperature_c for r in day_records if r.temperature_c is not None]
            hums = [r.humidity_percent for r in day_records if r.humidity_percent is not None]

            farm_trend["days"].append(
                {
                    "date": day_key,
                    "temp_avg": round(sum(temps) / len(temps), 1) if temps else None,
                    "humidity_avg": round(sum(hums) / len(hums), 1) if hums else None,
                }
            )

        daily_trends.append(farm_trend)

    # ─── SENSÖR OKUMA İSTATİSTİKLERİ ──────────────────────────────
    recent_readings = db.query(SoilMoistureReading).filter(SoilMoistureReading.reading_timestamp >= since).all()

    moisture_values = [r.moisture_percent for r in recent_readings if r.moisture_percent is not None]
    soil_temps = [r.soil_temperature_c for r in recent_readings if r.soil_temperature_c is not None]

    sensor_reading_stats = {
        "total_readings": len(recent_readings),
        "moisture": {
            "avg": round(sum(moisture_values) / len(moisture_values), 1) if moisture_values else None,
            "min": round(min(moisture_values), 1) if moisture_values else None,
            "max": round(max(moisture_values), 1) if moisture_values else None,
        },
        "soil_temperature": {
            "avg": round(sum(soil_temps) / len(soil_temps), 1) if soil_temps else None,
            "min": round(min(soil_temps), 1) if soil_temps else None,
            "max": round(max(soil_temps), 1) if soil_temps else None,
        },
    }

    # ─── NPK BİTKİ PROFİLLERİ (statik - radar chart için) ────────
    npk_profiles = [
        {"crop": "Buğday", "key": "wheat", "N": 120, "P": 60, "K": 40},
        {"crop": "Mısır", "key": "corn", "N": 180, "P": 80, "K": 60},
        {"crop": "Domates", "key": "tomato", "N": 150, "P": 100, "K": 200},
        {"crop": "Pamuk", "key": "cotton", "N": 140, "P": 60, "K": 80},
        {"crop": "Ayçiçeği", "key": "sunflower", "N": 100, "P": 70, "K": 50},
        {"crop": "Biber", "key": "pepper", "N": 130, "P": 80, "K": 160},
        {"crop": "Patates", "key": "potato", "N": 160, "P": 90, "K": 180},
        {"crop": "Pirinç", "key": "rice", "N": 140, "P": 50, "K": 40},
    ]

    return {
        "period_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": counts,
        "sensor_type_distribution": sensor_type_distribution,
        "farm_weather_comparison": farm_weather_comparison,
        "irrigation_status_distribution": irrigation_status_distribution,
        "daily_trends": daily_trends,
        "sensor_reading_stats": sensor_reading_stats,
        "npk_profiles": npk_profiles,
    }
