"""
Sensor API Endpoints — REBUILD Faz 1 RBAC
==========================================
CRUD for soil moisture / temperature sensors and their readings.

RBAC kapsamı (4 rol):
    farmer    → yalnız kendi field/sensor zinciri (read + write)
    developer → tüm sistem (test/integration namespace; write OK)
    overseer  → tüm sistem read-only (write 403)
    admin     → tüm sistem read + write
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import MAX_SQLITE_INT, get_db
from app.middleware.exceptions import NotFoundError
from app.middleware.rate_limiter import STRICT_RATE, limiter
from app.middleware.rbac import (
    assert_field_ownership,
    assert_sensor_ownership,
    require_write,
    scope_sensors_to_user,
)
from app.models.models import Sensor, SoilMoistureReading, User
from app.routers.auth import get_current_user_or_403
from app.schemas.schemas import SensorCreate, SensorReadingCreate, SensorReadingResponse, SensorResponse

router = APIRouter(prefix="/api/sensors", tags=["Sensör Verileri"])

# Pagination defaults — frontend pages through 50 records at a time.
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500
# 1M offset is far beyond any realistic pagination scenario; cap here
# avoids unbounded `skip` causing an int overflow on the DB binding.
MAX_SKIP = 1_000_000


@router.get(
    "/",
    response_model=list[SensorResponse],
    summary="Sensörleri listele (rol-aware pagination)",
    responses={401: {"description": "Bearer token gerekli"}},
)
def get_all_sensors(
    skip: int = Query(default=0, ge=0, le=MAX_SKIP),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> list[Sensor]:
    q = scope_sensors_to_user(db.query(Sensor), current_user)
    return q.order_by(Sensor.id).offset(skip).limit(limit).all()


@router.get(
    "/count",
    summary="Toplam sensör sayısı (rol-aware)",
    responses={401: {"description": "Bearer token gerekli"}},
)
def count_sensors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> dict:
    q = scope_sensors_to_user(db.query(func.count(Sensor.id)), current_user)
    return {"total": q.scalar() or 0}


@router.get(
    "/{sensor_id}",
    response_model=SensorResponse,
    summary="Tek bir sensörün detayı (rol-aware)",
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Farmer başkasının sensörüne erişemez"},
        404: {"description": "Sensor bulunamadı"},
    },
)
def get_sensor(
    sensor_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Sensor ID (max int64)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> Sensor:
    assert_sensor_ownership(db, sensor_id, current_user)
    sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if not sensor:
        raise NotFoundError("Sensör")
    return sensor


@router.post(
    "/",
    response_model=SensorResponse,
    status_code=201,
    summary="Yeni sensör ekle (rol-aware: farmer + admin)",
    responses={
        400: {"description": "Geçersiz JSON body"},
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Yazma yetkisi yok (overseer/developer)"},
        404: {"description": "Belirtilen field bulunamadı"},
        409: {"description": "Serial number zaten kayıtlı"},
    },
)
@limiter.limit(STRICT_RATE)
def create_sensor(
    request: Request,
    sensor: SensorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> Sensor:
    require_write(current_user)
    # Sensor.field_id sahibi olmalı (farmer için); admin bypass.
    assert_field_ownership(db, sensor.field_id, current_user)
    db_sensor = Sensor(**sensor.model_dump())
    db.add(db_sensor)
    db.commit()
    db.refresh(db_sensor)
    return db_sensor


@router.delete(
    "/{sensor_id}",
    summary="Sensör sil (rol-aware: farmer + admin)",
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Yazma yetkisi yok veya başkasının sensörü"},
        404: {"description": "Sensor bulunamadı"},
    },
)
@limiter.limit(STRICT_RATE)
def delete_sensor(
    request: Request,
    sensor_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Sensor ID (max int64)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> dict:
    require_write(current_user)
    assert_sensor_ownership(db, sensor_id, current_user)
    sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if not sensor:
        # assert_sensor_ownership zaten 404 fırlattı; race condition defensive.
        raise NotFoundError("Sensör")
    db.delete(sensor)
    db.commit()
    return {"message": "Sensor silindi"}


# ===== SENSOR READINGS =====
@router.post(
    "/readings",
    response_model=SensorReadingResponse,
    status_code=201,
    summary="Yeni sensör okuması kaydet (rol-aware)",
    responses={
        400: {"description": "Geçersiz JSON body"},
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Yazma yetkisi yok veya başkasının sensörü"},
        404: {"description": "Sensor bulunamadı"},
        409: {"description": "Veri çakışması"},
    },
)
@limiter.limit(STRICT_RATE)
def create_reading(
    request: Request,
    reading: SensorReadingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> SoilMoistureReading:
    require_write(current_user)
    assert_sensor_ownership(db, reading.sensor_id, current_user)
    db_reading = SoilMoistureReading(**reading.model_dump())
    db.add(db_reading)
    db.commit()
    db.refresh(db_reading)
    return db_reading


@router.get(
    "/{sensor_id}/readings",
    response_model=list[SensorReadingResponse],
    summary="Sensörün okumalarını listele (rol-aware)",
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Farmer başkasının sensörüne erişemez"},
        404: {"description": "Sensor bulunamadı"},
    },
)
def get_sensor_readings(
    sensor_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Sensor ID (max int64)"),
    limit: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> list[SoilMoistureReading]:
    assert_sensor_ownership(db, sensor_id, current_user)
    return (
        db.query(SoilMoistureReading)
        .filter(SoilMoistureReading.sensor_id == sensor_id)
        .order_by(SoilMoistureReading.reading_timestamp.desc())
        .limit(limit)
        .all()
    )
