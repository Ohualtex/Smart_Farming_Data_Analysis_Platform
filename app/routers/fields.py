"""
Field Detail API Endpoints — REBUILD Faz 3 Tarla Detay Sayfası
================================================================
Tek bir tarlanın tüm bağlamını tek çağrıda toplayan aggregated detay
endpoint'i. Demo akışının merkezi: dashboard "Tarla A susuz" → bu sayfa
→ yaprak foto upload (`/api/plants/health-images/analyze`) → tanı.

İçerik:
    - Tarla çekirdeği (ad, alan, toprak tipi, rakım)
    - Üst çiftlik (ad, bölge, il)
    - Ekili bitki türü (CropType)
    - Sensörler + her birinin en son okuması
    - Sulama geçmişi (en yeni N)
    - Bitki sağlığı/hastalık geçmişi (en yeni N)
    - Toprak analizleri (en yeni N)
    - Açık uyarılar (is_resolved=False)

RBAC kapsamı (assert_field_ownership ile):
    farmer    → yalnız kendi tarlası (Field → Farm → user_id)
    developer → tüm sistem (bypass)
    overseer  → tüm sistem (bypass)
    admin     → tüm sistem (bypass)

REBUILD_ROADMAP referansı: Faz 3 / Adım 1-2.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import MAX_SQLITE_INT, get_db
from app.middleware.rbac import assert_field_ownership
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
)
from app.routers.auth import get_current_user_or_403
from app.schemas.schemas import (
    FieldAlertSummary,
    FieldCropInfo,
    FieldDetailResponse,
    FieldDiseaseSummary,
    FieldIrrigationSummary,
    FieldSensorSummary,
    SoilAnalysisResponse,
)

router = APIRouter(prefix="/api/fields", tags=["Tarla Detayı"])

# ─── Sabitler ──────────────────────────────────────────────────
# Dashboard ile aynı nem eşikleri (dashboard.py ile senkron tutulmalı).
SOIL_MOISTURE_DRY_THRESHOLD = 30.0
SOIL_MOISTURE_WET_THRESHOLD = 70.0
SOIL_MOISTURE_WINDOW_HOURS = 24
# Koleksiyon limitleri — detay sayfası "son N" gösterir, tümünü değil.
RECENT_IRRIGATION_LIMIT = 10
DISEASE_HISTORY_LIMIT = 10
SOIL_ANALYSES_LIMIT = 5


def _classify_moisture(avg: float | None) -> str:
    """Ortalama nem → 'dry' / 'optimal' / 'wet' / 'no_data' kategorisi."""
    if avg is None:
        return "no_data"
    if avg < SOIL_MOISTURE_DRY_THRESHOLD:
        return "dry"
    if avg > SOIL_MOISTURE_WET_THRESHOLD:
        return "wet"
    return "optimal"


@router.get(
    "/{field_id}",
    response_model=FieldDetailResponse,
    summary="Tarla detayı — sensör, sulama, hastalık, toprak, uyarı (rol-aware)",
    description=(
        "Tek tarlanın tüm bağlamını tek çağrıda toplar. Farmer yalnız kendi "
        "tarlasını görebilir (Field → Farm → user_id sahiplik kontrolü); "
        "admin/overseer/developer tüm tarlalara erişir. Sensörler en son "
        "okumalarıyla, sulama/hastalık/toprak geçmişi en yeniden eskiye sıralı."
    ),
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Farmer başkasının tarlasına erişemez"},
        404: {"description": "Tarla bulunamadı"},
    },
)
def get_field_detail(
    field_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Tarla ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> FieldDetailResponse:
    """Tarla detayını topla. Sahiplik kontrolü önce; sonra aggregation."""
    # 404/403 sahiplik kontrolü — farmer kendi tarlası dışına erişemez.
    assert_field_ownership(db, field_id, current_user)

    # ─── Tarla + üst çiftlik + bitki (tek join) ──────────────────
    row = (
        db.query(Field, Farm, CropType)
        .join(Farm, Field.farm_id == Farm.id)
        .outerjoin(CropType, Field.crop_id == CropType.id)
        .filter(Field.id == field_id)
        .first()
    )
    if row is None:
        # assert_field_ownership zaten 404 fırlattı; defensive (race).
        raise HTTPException(status_code=404, detail="Tarla bulunamadi")
    field, farm, crop = row

    # ─── Sensörler + her birinin en son okuması ──────────────────
    sensors = db.query(Sensor).filter(Sensor.field_id == field_id).order_by(Sensor.id).all()
    sensor_summaries: list[FieldSensorSummary] = []
    for sensor in sensors:
        latest = (
            db.query(SoilMoistureReading)
            .filter(SoilMoistureReading.sensor_id == sensor.id)
            .order_by(SoilMoistureReading.reading_timestamp.desc())
            .first()
        )
        sensor_summaries.append(
            FieldSensorSummary(
                id=sensor.id,
                sensor_type=sensor.sensor_type,
                serial_number=sensor.serial_number,
                status=sensor.status,
                latest_moisture_percent=latest.moisture_percent if latest else None,
                latest_soil_temperature_c=latest.soil_temperature_c if latest else None,
                latest_reading_at=latest.reading_timestamp if latest else None,
            )
        )

    # ─── Toprak nemi özeti (son 24 saat, bu tarlanın sensörleri) ─
    since = datetime.now(UTC) - timedelta(hours=SOIL_MOISTURE_WINDOW_HOURS)
    avg_moisture = (
        db.query(func.avg(SoilMoistureReading.moisture_percent))
        .join(Sensor, SoilMoistureReading.sensor_id == Sensor.id)
        .filter(Sensor.field_id == field_id, SoilMoistureReading.reading_timestamp >= since)
        .scalar()
    )

    # ─── Sulama geçmişi ──────────────────────────────────────────
    irrigations = (
        db.query(IrrigationSchedule)
        .filter(IrrigationSchedule.field_id == field_id)
        .order_by(IrrigationSchedule.scheduled_date.desc())
        .limit(RECENT_IRRIGATION_LIMIT)
        .all()
    )

    # ─── Hastalık geçmişi ────────────────────────────────────────
    diseases = (
        db.query(PlantHealthImage)
        .filter(PlantHealthImage.field_id == field_id)
        .order_by(PlantHealthImage.captured_at.desc())
        .limit(DISEASE_HISTORY_LIMIT)
        .all()
    )

    # ─── Toprak analizleri ───────────────────────────────────────
    soil_analyses = (
        db.query(SoilAnalysis)
        .filter(SoilAnalysis.field_id == field_id)
        .order_by(SoilAnalysis.analysis_date.desc())
        .limit(SOIL_ANALYSES_LIMIT)
        .all()
    )

    # ─── Açık uyarılar (bu tarlaya bağlı) ────────────────────────
    open_alerts = (
        db.query(SystemAlert)
        .filter(SystemAlert.field_id == field_id, SystemAlert.is_resolved.is_(False))
        .order_by(SystemAlert.created_at.desc())
        .all()
    )

    return FieldDetailResponse(
        id=field.id,
        name=field.name,
        area_hectares=field.area_hectares,
        soil_type=field.soil_type,
        elevation_m=field.elevation_m,
        farm_id=farm.id,
        farm_name=farm.name,
        region=farm.region,
        city=farm.city,
        crop=FieldCropInfo.model_validate(crop) if crop else None,
        moisture_status=_classify_moisture(avg_moisture),
        avg_moisture_percent=round(avg_moisture, 1) if avg_moisture is not None else None,
        sensors=sensor_summaries,
        recent_irrigations=[FieldIrrigationSummary.model_validate(i) for i in irrigations],
        disease_history=[FieldDiseaseSummary.model_validate(d) for d in diseases],
        soil_analyses=[SoilAnalysisResponse.model_validate(s) for s in soil_analyses],
        open_alerts=[FieldAlertSummary.model_validate(a) for a in open_alerts],
        generated_at=datetime.now(UTC),
    )


@router.get(
    "/{field_id}/readings",
    summary="Tarlanın sensör okuma zaman serisi (grafik için, rol-aware)",
    description=(
        "Tarladaki tüm sensörlerin son N okumasını zaman sırasıyla döner — "
        "detay sayfasındaki nem trend grafiği için. Farmer yalnız kendi tarlası."
    ),
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Farmer başkasının tarlasına erişemez"},
        404: {"description": "Tarla bulunamadı"},
    },
)
def get_field_readings(
    field_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Tarla ID"),
    limit: int = Query(default=50, ge=1, le=500, description="Okuma sayısı"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> list[dict]:
    """Tarlanın sensör okumalarını zaman sırasıyla (en eskiden yeniye) döndür."""
    assert_field_ownership(db, field_id, current_user)
    rows = (
        db.query(SoilMoistureReading, Sensor.sensor_type)
        .join(Sensor, SoilMoistureReading.sensor_id == Sensor.id)
        .filter(Sensor.field_id == field_id)
        .order_by(SoilMoistureReading.reading_timestamp.desc())
        .limit(limit)
        .all()
    )
    # En yeniden çektik; grafik için kronolojik (eskiden yeniye) ters çevir.
    result = [
        {
            "reading_timestamp": str(reading.reading_timestamp),
            "sensor_id": reading.sensor_id,
            "sensor_type": sensor_type,
            "moisture_percent": reading.moisture_percent,
            "soil_temperature_c": reading.soil_temperature_c,
        }
        for reading, sensor_type in rows
    ]
    result.reverse()
    return result
