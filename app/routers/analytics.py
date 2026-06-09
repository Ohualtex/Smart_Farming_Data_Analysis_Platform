"""
Analytics API Endpoints — REBUILD Faz 1 RBAC
==============================================
Görselleştirme dashboard'u için toplu istatistik ve içgörü uçları.

RBAC kapsamı: **admin / overseer / developer only** — sistem-geneli
aggregate'ler farmer scope'una uygun değil (joins/counts karmaşık).
Farmer için "Bugünün durumu" Faz 2'de `/api/dashboard/today` endpoint'i
ile gelecek (farmer'ın kendi farm'larındaki kompakt özet).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.exceptions import ValidationError
from app.models.models import (
    Farm,
    Field,
    IrrigationSchedule,
    Sensor,
    SoilMoistureReading,
    User,
    WeatherData,
)
from app.routers.auth import require_role
from app.schemas.base import _serialize_utc
from app.services.report_service import ReportService

router = APIRouter(prefix="/api/analytics", tags=["Analitik & Görselleştirme"])


@router.get(
    "/summary",
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Farmer analytics'e erişemez (sistem-geneli aggregate)"},
    },
)
def get_analytics_summary(
    days: int = Query(default=30, ge=1, le=365, description="Son kaç gün"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin", "overseer", "developer")),
) -> dict:
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
    since = datetime.now(UTC) - timedelta(days=days)

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

    # ─── HAVA DURUMU VERİLERİNİ TEK SORGUDA ÇEK ──────────────────
    # N+1 önleme: Önceki yaklaşım her çiftlik için ayrı sorgu yapıyordu
    # (çok-çiftlik senaryosunda 1 + 2N query). Şimdi tüm 'since' sonrası
    # WeatherData kayıtlarını tek sorguda alıp Python'da farm_id ile gruplandırıyoruz.
    # EN: N+1 fix — was 1 + 2N queries; now 1 + 1 = 2.
    farms = db.query(Farm).all()
    all_weather_records = db.query(WeatherData).filter(WeatherData.recorded_at >= since).all()

    records_by_farm: dict[int, list[WeatherData]] = {}
    for record in all_weather_records:
        if record.farm_id is None:
            continue
        records_by_farm.setdefault(record.farm_id, []).append(record)

    # ─── ÇİFTLİK BAZLI HAVA DURUMU KARŞILAŞTIRMASI ───────────────
    farm_weather_comparison = []
    for farm in farms:
        weather_records = records_by_farm.get(farm.id, [])
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
    # Aynı `records_by_farm` dict'ini yeniden kullanıyoruz; ek sorgu yok.
    daily_trends = []
    for farm in farms:
        records = records_by_farm.get(farm.id, [])
        if not records:
            continue

        # Günlük grupla (in-memory; tarih sıralı erişim için sort)
        records_sorted = sorted(records, key=lambda r: r.recorded_at or datetime.min.replace(tzinfo=UTC))
        day_groups: dict[str, list] = {}
        for r in records_sorted:
            if r.recorded_at:
                day_key = r.recorded_at.strftime("%Y-%m-%d")
                day_groups.setdefault(day_key, []).append(r)

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
    # AUDIT #22: tüm okumaları belleğe çekmek yerine SQL aggregate (365 güne kadar,
    # potansiyel on binlerce satır). AVG/MIN/MAX NULL'ları yok sayar (Python'daki
    # non-null filtresiyle aynı sonuç); COUNT tüm satırları sayar. Değerler değişmez.
    reading_agg = (
        db.query(
            func.count(SoilMoistureReading.id),
            func.avg(SoilMoistureReading.moisture_percent),
            func.min(SoilMoistureReading.moisture_percent),
            func.max(SoilMoistureReading.moisture_percent),
            func.avg(SoilMoistureReading.soil_temperature_c),
            func.min(SoilMoistureReading.soil_temperature_c),
            func.max(SoilMoistureReading.soil_temperature_c),
        )
        .filter(SoilMoistureReading.reading_timestamp >= since)
        .one()
    )

    def _r1(v: float | None) -> float | None:
        return round(v, 1) if v is not None else None

    sensor_reading_stats = {
        "total_readings": int(reading_agg[0] or 0),
        "moisture": {"avg": _r1(reading_agg[1]), "min": _r1(reading_agg[2]), "max": _r1(reading_agg[3])},
        "soil_temperature": {"avg": _r1(reading_agg[4]), "min": _r1(reading_agg[5]), "max": _r1(reading_agg[6])},
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
        "generated_at": datetime.now(UTC).isoformat(),
        "counts": counts,
        "sensor_type_distribution": sensor_type_distribution,
        "farm_weather_comparison": farm_weather_comparison,
        "irrigation_status_distribution": irrigation_status_distribution,
        "daily_trends": daily_trends,
        "sensor_reading_stats": sensor_reading_stats,
        "npk_profiles": npk_profiles,
    }


@router.get(
    "/compare",
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Farmer compare'e erişemez (sistem-geneli aggregate)"},
    },
)
def compare_analytics(
    start_date_1: datetime = Query(..., description="1. Periyot Baslangic (Orn: 2026-03-01T00:00:00Z)"),
    end_date_1: datetime = Query(..., description="1. Periyot Bitis (Orn: 2026-03-31T23:59:59Z)"),
    start_date_2: datetime = Query(..., description="2. Periyot Baslangic"),
    end_date_2: datetime = Query(..., description="2. Periyot Bitis"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin", "overseer", "developer")),
) -> dict:
    """
    Kullanicinin belirledigi iki farkli zaman dilimini kiyaslar.
    Sicaklik, nem, sensor okumasi ve sulama sayisi gibi metrikleri
    fark (yuzdelik artis/azalis) ile dondurur.
    """

    def _get_stats(start: datetime, end: datetime):
        # AUDIT #22: SQL aggregate (belleğe satır çekmeden). AVG NULL'ları yok sayar
        # (Python non-null filtresiyle aynı); SUM tümü NULL/boşsa None → 0.0'a düşülür.
        weather_agg = (
            db.query(
                func.avg(WeatherData.temperature_c),
                func.avg(WeatherData.humidity_percent),
                func.sum(WeatherData.precipitation_mm),
            )
            .filter(WeatherData.recorded_at >= start, WeatherData.recorded_at <= end)
            .one()
        )
        temp_avg_v, humidity_avg_v, precip = weather_agg[0], weather_agg[1], (weather_agg[2] or 0.0)

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
            # AUDIT FIX (#5): boş periyotta ortalama 0 yerine None döner;
            # aksi halde _diff 0'ı gerçek baseline sanıp sahte %100 üretiyordu.
            "temp_avg": round(temp_avg_v, 2) if temp_avg_v is not None else None,
            "humidity_avg": round(humidity_avg_v, 2) if humidity_avg_v is not None else None,
            "precipitation_mm": round(precip, 2),
            "sensor_readings": readings,
            "irrigations": irrigations,
        }

    stats_1 = _get_stats(start_date_1, end_date_1)
    stats_2 = _get_stats(start_date_2, end_date_2)

    def _diff(val1: float | None, val2: float | None) -> float | None:
        # AUDIT FIX (#5): baseline/current veri yoksa (None) veya baseline 0 ise
        # anlamlı bir yüzde hesaplanamaz → None.
        if val1 is None or val2 is None or val1 == 0:
            return None
        # AUDIT FIX (#4): negatif baseline'da yüzdenin işareti ters dönmesin diye
        # paydada abs(val1) kullanılır; pay işareti (val2 - val1) korunur.
        return round(((val2 - val1) / abs(val1)) * 100, 2)

    return {
        # AUDIT FIX (L6): raw dict → datetime'ler tz'siz dönüyordu (UTC offset yok).
        # API'nin geri kalanıyla uyumlu ISO 8601 (UTC suffix'li) için _serialize_utc.
        "period_1": {
            "start": _serialize_utc(start_date_1),
            "end": _serialize_utc(end_date_1),
            "stats": stats_1,
        },
        "period_2": {
            "start": _serialize_utc(start_date_2),
            "end": _serialize_utc(end_date_2),
            "stats": stats_2,
        },
        "comparison": {
            "temp_avg_diff_percent": _diff(stats_1["temp_avg"], stats_2["temp_avg"]),
            "humidity_avg_diff_percent": _diff(stats_1["humidity_avg"], stats_2["humidity_avg"]),
            "precipitation_diff_percent": _diff(stats_1["precipitation_mm"], stats_2["precipitation_mm"]),
            "sensor_readings_diff_percent": _diff(stats_1["sensor_readings"], stats_2["sensor_readings"]),
            "irrigations_diff_percent": _diff(stats_1["irrigations"], stats_2["irrigations"]),
        },
    }


@router.get(
    "/export",
    responses={
        200: {
            "content": {
                "application/pdf": {},
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {},
            },
            "description": "Üretilen rapor (`format` query'sine göre PDF veya XLSX).",
        },
        400: {"description": "Geçersiz format değeri"},
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Farmer export'a erişemez"},
    },
)
def export_analytics(
    format: str = Query("pdf", description="Export formati (pdf veya xlsx)"),
    days: int = Query(30, ge=1, le=365, description="Son kac gunluk veri (max 365)"),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "overseer", "developer")),
) -> StreamingResponse:
    """Analitik verilerini PDF veya Excel formati olarak disari aktarir."""
    if format not in ["pdf", "xlsx"]:
        raise ValidationError(message="Geçersiz format. Sadece 'pdf' veya 'xlsx' desteklenir.")

    # `get_analytics_summary` artık `_user` Depends gerektiriyor; export
    # zaten authorized caller'ı geçirir.
    data = get_analytics_summary(days=days, db=db, _user=user)

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
