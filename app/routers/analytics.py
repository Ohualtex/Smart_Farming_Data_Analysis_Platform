"""
Analytics API Endpoint'leri
=============================
Veri görselleştirme panosu için toplu istatistik ve
içgörü verileri döndüren endpoint'ler.

Miraç Duran — Cycle 6 Görevi
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
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
from app.services.report_service import ReportService

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
                "region": farm.region,
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
            "region": farm.region,
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


@router.get("/compare")
def compare_analytics(
    start_date_1: datetime = Query(..., description="1. Periyot Baslangic (Orn: 2026-03-01T00:00:00Z)"),
    end_date_1: datetime = Query(..., description="1. Periyot Bitis (Orn: 2026-03-31T23:59:59Z)"),
    start_date_2: datetime = Query(..., description="2. Periyot Baslangic"),
    end_date_2: datetime = Query(..., description="2. Periyot Bitis"),
    db: Session = Depends(get_db),
):
    """
    Kullanicinin belirledigi iki farkli zaman dilimini kiyaslar.
    Sicaklik, nem, sensor okumasi ve sulama sayisi gibi metrikleri
    fark (yuzdelik artis/azalis) ile dondurur.
    """

    def _get_stats(start: datetime, end: datetime):
        weather_records = (
            db.query(WeatherData).filter(WeatherData.recorded_at >= start, WeatherData.recorded_at <= end).all()
        )

        temps = [r.temperature_c for r in weather_records if r.temperature_c is not None]
        hums = [r.humidity_percent for r in weather_records if r.humidity_percent is not None]
        precip = sum([r.precipitation_mm for r in weather_records if r.precipitation_mm is not None])

        readings = (
            db.query(func.count(SoilMoistureReading.id))
            .filter(SoilMoistureReading.reading_timestamp >= start, SoilMoistureReading.reading_timestamp <= end)
            .scalar()
            or 0
        )

        irrigations = (
            db.query(func.count(IrrigationSchedule.id))
            .filter(IrrigationSchedule.scheduled_date >= start, IrrigationSchedule.scheduled_date <= end)
            .scalar()
            or 0
        )

        return {
            "temp_avg": round(sum(temps) / len(temps), 2) if temps else 0,
            "humidity_avg": round(sum(hums) / len(hums), 2) if hums else 0,
            "precipitation_mm": round(precip, 2),
            "sensor_readings": readings,
            "irrigations": irrigations,
        }

    stats_1 = _get_stats(start_date_1, end_date_1)
    stats_2 = _get_stats(start_date_2, end_date_2)

    def _diff(val1, val2):
        if val1 == 0:
            return 100.0 if val2 > 0 else 0.0
        return round(((val2 - val1) / val1) * 100, 2)

    return {
        "period_1": {"start": start_date_1, "end": end_date_1, "stats": stats_1},
        "period_2": {"start": start_date_2, "end": end_date_2, "stats": stats_2},
        "comparison": {
            "temp_avg_diff_percent": _diff(stats_1["temp_avg"], stats_2["temp_avg"]),
            "humidity_avg_diff_percent": _diff(stats_1["humidity_avg"], stats_2["humidity_avg"]),
            "precipitation_diff_percent": _diff(stats_1["precipitation_mm"], stats_2["precipitation_mm"]),
            "sensor_readings_diff_percent": _diff(stats_1["sensor_readings"], stats_2["sensor_readings"]),
            "irrigations_diff_percent": _diff(stats_1["irrigations"], stats_2["irrigations"]),
        },
    }


@router.get("/export")
def export_analytics(
    format: str = Query("pdf", description="Export formati (pdf veya xlsx)"),
    days: int = Query(30, description="Son kac gunluk veri"),
    db: Session = Depends(get_db),
):
    """
    Analitik verilerini PDF veya Excel formati olarak disari aktarir.
    """
    if format not in ["pdf", "xlsx"]:
        raise HTTPException(status_code=400, detail="Gecersiz format. Sadece 'pdf' veya 'xlsx' desteklenir.")

    data = get_analytics_summary(days=days, db=db)

    if format == "pdf":
        file_stream = ReportService.generate_pdf_report(data)
        media_type = "application/pdf"
        filename = f"sfdap_analitik_rapor_{days}_gun.pdf"
    else:
        file_stream = ReportService.generate_excel_report(data)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"sfdap_analitik_rapor_{days}_gun.xlsx"

    return StreamingResponse(
        file_stream, media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
