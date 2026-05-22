"""
Dashboard API Endpoints — REBUILD Faz 2 "Çiftliğim" özet
==========================================================
Rol-aware tek-ekran çiftçi/sistem dashboard'u. Frontend, farmer
kullanıcısı için kendi farm zinciri özetini; admin/overseer/developer
için sistem-geneli toplamı render eder. Tek endpoint, tek schema —
istemci `scope` alanından hangi bağlamı gösterdiğini bilir.

RBAC kapsamı:
    farmer    → kendi farm zinciri (Farm.user_id == user.id)
    developer → sistem-geneli (read-only audit)
    overseer  → sistem-geneli (read-only)
    admin     → sistem-geneli (full)

4 metrik:
    1. soil_moisture_today  — son 24 saat ortalama nem (status: dry/optimal/wet)
    2. last_irrigation      — en yeni IrrigationSchedule satırı
    3. open_alerts          — is_resolved=False sayım + severity kırılımı
    4. last_disease         — en yeni PlantHealthImage tanısı

REBUILD_ROADMAP referansı: Faz 2 / Adım 1-2.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import (
    Farm,
    Field,
    IrrigationSchedule,
    PlantHealthImage,
    Sensor,
    SoilMoistureReading,
    SystemAlert,
    User,
)
from app.routers.auth import get_current_user_or_403
from app.schemas.schemas import (
    DashboardLastDisease,
    DashboardLastIrrigation,
    DashboardOpenAlerts,
    DashboardSoilMoisture,
    DashboardSummaryResponse,
)

router = APIRouter(prefix="/api/dashboard", tags=["Çiftliğim"])

# ─── Sabitler ──────────────────────────────────────────────────
# Nem eşikleri — "optimal" bandı 30-70%. Kaynak: Faz 1'de irrigation_service
# içinde kullanılan eşiklerle hizalı; eşikler degişirse hem orada hem burada
# güncellenmeli.
SOIL_MOISTURE_DRY_THRESHOLD = 30.0
SOIL_MOISTURE_WET_THRESHOLD = 70.0
# "Bugün" penceresi — son 24 saat; tek-gün UTC sınırı yerine sliding window
# çünkü farmer farklı saat diliminde olabilir ve "bugün" göreceli.
SOIL_MOISTURE_WINDOW_HOURS = 24


def _classify_moisture(avg: float | None) -> str:
    """Ortalama nem → 'dry' / 'optimal' / 'wet' / 'no_data' kategorisi."""
    if avg is None:
        return "no_data"
    if avg < SOIL_MOISTURE_DRY_THRESHOLD:
        return "dry"
    if avg > SOIL_MOISTURE_WET_THRESHOLD:
        return "wet"
    return "optimal"


def _is_system_scope(user: User) -> bool:
    """admin/overseer/developer → sistem-geneli; farmer → kendi farm zinciri."""
    return user.role in ("admin", "overseer", "developer")


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Çiftliğim — rol-aware tek-ekran özet",
    description=(
        "Authenticated kullanıcı için 'Çiftliğim' özet ekranı (4 metrik + sayımlar). "
        "Farmer rolünde kendi farm zincirine filtrelenir; admin/overseer/developer "
        "için sistem-geneli toplam döner. `scope` alanı hangi bağlamın aktif "
        "olduğunu söyler ('user' veya 'system')."
    ),
    responses={
        401: {"description": "Bearer token gerekli"},
    },
)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> DashboardSummaryResponse:
    """Rol-aware dashboard özetini hesapla.

    Single round-trip yaklaşımı: her metrik için tek query yapılır
    (toplam 7 query). Farmer scope'unda Farm.user_id == user.id filter
    her query'nin başına eklenir.
    """
    is_system = _is_system_scope(current_user)
    now = datetime.now(UTC)
    since = now - timedelta(hours=SOIL_MOISTURE_WINDOW_HOURS)

    # ─── Sayımlar (farm / field / sensor) ────────────────────────
    farm_q = db.query(func.count(Farm.id))
    field_q = db.query(func.count(Field.id)).join(Farm, Field.farm_id == Farm.id)
    sensor_q = (
        db.query(func.count(Sensor.id)).join(Field, Sensor.field_id == Field.id).join(Farm, Field.farm_id == Farm.id)
    )
    if not is_system:
        farm_q = farm_q.filter(Farm.user_id == current_user.id)
        field_q = field_q.filter(Farm.user_id == current_user.id)
        sensor_q = sensor_q.filter(Farm.user_id == current_user.id)
    farm_count = farm_q.scalar() or 0
    field_count = field_q.scalar() or 0
    sensor_count = sensor_q.scalar() or 0

    # ─── 1. Toprak nemi (son 24 saat) ────────────────────────────
    # Tek aggregate query: avg, count, distinct sensor count, max timestamp.
    moisture_q = (
        db.query(
            func.avg(SoilMoistureReading.moisture_percent),
            func.count(SoilMoistureReading.id),
            func.count(func.distinct(SoilMoistureReading.sensor_id)),
            func.max(SoilMoistureReading.reading_timestamp),
        )
        .join(Sensor, SoilMoistureReading.sensor_id == Sensor.id)
        .join(Field, Sensor.field_id == Field.id)
        .join(Farm, Field.farm_id == Farm.id)
        .filter(SoilMoistureReading.reading_timestamp >= since)
    )
    if not is_system:
        moisture_q = moisture_q.filter(Farm.user_id == current_user.id)
    avg_moisture, reading_count, sensor_with_data, last_reading = moisture_q.one()
    soil_moisture = DashboardSoilMoisture(
        avg_moisture_percent=round(avg_moisture, 1) if avg_moisture is not None else None,
        reading_count=int(reading_count or 0),
        sensor_count=int(sensor_with_data or 0),
        last_reading_at=last_reading,
        status=_classify_moisture(avg_moisture),
    )

    # ─── 2. Son sulama ───────────────────────────────────────────
    irrigation_q = (
        db.query(IrrigationSchedule, Field.name)
        .join(Field, IrrigationSchedule.field_id == Field.id)
        .join(Farm, Field.farm_id == Farm.id)
    )
    if not is_system:
        irrigation_q = irrigation_q.filter(Farm.user_id == current_user.id)
    irrigation_row = irrigation_q.order_by(IrrigationSchedule.scheduled_date.desc()).first()
    if irrigation_row is not None:
        schedule, field_name = irrigation_row
        last_irrigation = DashboardLastIrrigation(
            irrigation_id=schedule.id,
            field_id=schedule.field_id,
            field_name=field_name,
            scheduled_date=schedule.scheduled_date,
            water_amount_liters=schedule.water_amount_liters,
            status=schedule.status,
        )
    else:
        last_irrigation = DashboardLastIrrigation()

    # ─── 3. Açık uyarılar (sayım + severity kırılım + en yeni) ───
    # Farmer: yalnız kendi farm'larına bağlı; system-wide alert (farm_id=None)
    # farmer'a görünmez (alerts router'ı ile aynı kural).
    alerts_base = db.query(SystemAlert).filter(SystemAlert.is_resolved.is_(False))
    if not is_system:
        alerts_base = alerts_base.join(Farm, SystemAlert.farm_id == Farm.id).filter(Farm.user_id == current_user.id)
    # severity dağılımı tek query'de GROUP BY
    severity_rows = (
        alerts_base.with_entities(SystemAlert.severity, func.count(SystemAlert.id)).group_by(SystemAlert.severity).all()
    )
    by_severity: dict[str, int] = {"low": 0, "medium": 0, "critical": 0}
    total_alerts = 0
    for sev, cnt in severity_rows:
        # Beklenmeyen severity ('info' gibi legacy değerler) korunsun
        by_severity[sev] = by_severity.get(sev, 0) + int(cnt)
        total_alerts += int(cnt)
    latest_alert = alerts_base.order_by(SystemAlert.created_at.desc()).first()
    open_alerts = DashboardOpenAlerts(
        total=total_alerts,
        by_severity=by_severity,
        latest_message=latest_alert.message if latest_alert else None,
        latest_severity=latest_alert.severity if latest_alert else None,
        latest_created_at=latest_alert.created_at if latest_alert else None,
    )

    # ─── 4. Son hastalık tanısı ──────────────────────────────────
    disease_q = (
        db.query(PlantHealthImage, Field.name)
        .join(Field, PlantHealthImage.field_id == Field.id)
        .join(Farm, Field.farm_id == Farm.id)
        .filter(PlantHealthImage.diagnosis.isnot(None))
    )
    if not is_system:
        disease_q = disease_q.filter(Farm.user_id == current_user.id)
    disease_row = disease_q.order_by(PlantHealthImage.captured_at.desc()).first()
    if disease_row is not None:
        img, field_name = disease_row
        last_disease = DashboardLastDisease(
            image_id=img.id,
            field_id=img.field_id,
            field_name=field_name,
            captured_at=img.captured_at,
            diagnosis=img.diagnosis,
            severity=img.severity,
            confidence_score=img.confidence_score,
        )
    else:
        last_disease = DashboardLastDisease()

    return DashboardSummaryResponse(
        user_name=current_user.name,
        user_role=current_user.role,
        scope="system" if is_system else "user",
        farm_count=farm_count,
        field_count=field_count,
        sensor_count=sensor_count,
        soil_moisture_today=soil_moisture,
        last_irrigation=last_irrigation,
        open_alerts=open_alerts,
        last_disease=last_disease,
        generated_at=now,
    )
