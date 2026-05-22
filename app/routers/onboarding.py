"""
Onboarding API Endpoints — REBUILD Faz 6
==========================================
Yeni kullanıcı için tek-tık örnek (demo) veri kurulumu. Boş hesapla giriş
yapan çiftçi "Demo verisi yükle" diyerek kendi adına gerçekçi bir çiftlik +
tarla + sensör/okuma + uyarı seti alır ve platformu anında keşfedebilir.

RBAC kapsamı:
    farmer / admin → kendi adına demo veri kurar (write set)
    overseer / developer → 403 (read-only roller)

Idempotency: kullanıcının zaten çiftliği varsa 409 (demo veri yalnız boş
hesaba kurulur; mevcut veriyi kirletmez).
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rate_limiter import STRICT_RATE, limiter
from app.middleware.rbac import _WRITE_ROLES
from app.models.models import (
    CropType,
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

router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])

# Demo tarla tanımı: (ad, toprak, alan, taban_nem%) — taban_nem status belirler
# (<30 dry → kritik uyarı tetikler; >30 optimal).
_DEMO_FIELDS = [
    ("Tarla A", "killi", 3.5, 22.0),  # susuz → demo akışının "Tarla A susuz" adımı
    ("Tarla B", "tınlı", 2.0, 52.0),  # uygun
]


def _require_write(user: User) -> None:
    """overseer/developer için 403; farmer + admin OK."""
    if user.role not in _WRITE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Yazma yetkisi yok (rol: {user.role}); farmer veya admin gerek",
        )


def _diurnal_factor(hour: int) -> float:
    """Günlük döngü faktörü: -1 (gece dip) ↔ +1 (öğle pik)."""
    return math.sin(2 * math.pi * (hour - 6) / 24)


@router.post(
    "/demo",
    status_code=201,
    summary="Tek-tık demo verisi kur (rol-aware, idempotent)",
    description=(
        "Boş hesaba giriş yapan kullanıcı için kendi adına 1 çiftlik + 2 tarla "
        "(biri susuz/biri uygun) + sensör + son 24 saatlik okuma + kritik uyarı kurar. "
        "Çiftliği olan kullanıcı 409 alır (mevcut veri korunur). farmer + admin; "
        "overseer/developer 403."
    ),
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Yazma yetkisi yok (overseer/developer)"},
        409: {"description": "Kullanıcının zaten çiftliği var"},
    },
)
@limiter.limit(STRICT_RATE)
def load_demo_data(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> dict:
    """current_user adına demo çiftlik zincirini kur (yalnız boş hesaba)."""
    _require_write(current_user)

    existing = db.query(func.count(Farm.id)).filter(Farm.user_id == current_user.id).scalar() or 0
    if existing > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Zaten çiftliğin var; demo veri yalnız boş hesaba kurulur.",
        )

    now = datetime.now(UTC)

    # Bitki türü referansı (varsa kullan; yoksa demo için 1 tane oluştur)
    wheat = db.query(CropType).filter(CropType.name == "Buğday").first()
    if wheat is None:
        wheat = CropType(name="Buğday", scientific_name="Triticum aestivum", water_need_mm_per_day=4.5)
        db.add(wheat)
        db.flush()

    farm = Farm(
        user_id=current_user.id,
        name="Demo Çiftliğim",
        city="Konya",
        region="İç Anadolu",
        location_lat=37.87,
        location_lng=32.48,
        area_hectares=6.0,
    )
    db.add(farm)
    db.flush()

    first_field_id = None
    for fname, soil, area, base_moisture in _DEMO_FIELDS:
        field = Field(
            farm_id=farm.id,
            name=fname,
            soil_type=soil,
            area_hectares=area,
            elevation_m=1020.0,
            crop_id=wheat.id,
        )
        db.add(field)
        db.flush()
        if first_field_id is None:
            first_field_id = field.id

        sensor = Sensor(
            field_id=field.id,
            sensor_type="soil_moisture",
            serial_number=f"DEMO-{current_user.id}-{field.id}",
            status="active",
        )
        db.add(sensor)
        db.flush()

        # Son 24 saat, 2 saatte bir diurnal okuma
        for h in range(0, 24, 2):
            moisture = base_moisture + _diurnal_factor((now.hour - h) % 24) * 3
            db.add(
                SoilMoistureReading(
                    sensor_id=sensor.id,
                    reading_timestamp=now - timedelta(hours=h),
                    moisture_percent=round(max(0.0, min(100.0, moisture)), 1),
                    soil_temperature_c=18.0,
                )
            )

        # Susuz tarla için kritik uyarı + tamamlanmış bir sulama; uygun tarla
        # için yakın hastalık analizi (demo akışı zenginliği)
        if base_moisture < 30:
            db.add(
                SystemAlert(
                    farm_id=farm.id,
                    field_id=field.id,
                    alert_type="low_moisture",
                    severity="critical",
                    message=f"{fname}: toprak nemi düşük — sulama önerilir.",
                    is_resolved=False,
                )
            )
            db.add(
                IrrigationSchedule(
                    field_id=field.id,
                    scheduled_date=now - timedelta(days=2),
                    water_amount_liters=250.0,
                    duration_min=45,
                    status="completed",
                    source="model",
                )
            )
        else:
            db.add(
                PlantHealthImage(
                    field_id=field.id,
                    image_url="/static/plant_uploads/demo_leaf.jpg",
                    captured_at=now - timedelta(days=1),
                    diagnosis="healthy",
                    confidence_score=0.95,
                    severity="none",
                )
            )

    db.commit()
    return {
        "message": "Demo verisi kuruldu",
        "farm_id": farm.id,
        "fields_created": len(_DEMO_FIELDS),
        "first_field_id": first_field_id,
    }
