"""
Sensör API Endpoint'leri
==========================
Toprak nem / sıcaklık sensörlerinin CRUD işlemleri ve okuma kayıtları.
Yazma işlemleri (POST/DELETE) için X-API-Key auth zorunludur.

Emirhan Günay & Mehmet Sait Tayşi — Cycle 4 Görevi
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import verify_api_key
from app.middleware.rate_limiter import STRICT_RATE, limiter
from app.models.models import Sensor, SoilMoistureReading
from app.schemas.schemas import SensorCreate, SensorReadingCreate, SensorReadingResponse, SensorResponse

router = APIRouter(prefix="/api/sensors", tags=["Sensör Verileri"])

# Pagination defaults — frontend slider 50'lik sayfalarla çalışıyor
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500
# shiftFinal Ayşe — Schemathesis fuzz, unbounded `skip` ile int64 overflow
# yakaladi (SQLite INTEGER taşıyor). 1M offset gerçekçi her kullanım için
# fazlasıyla yeterli (PAGE_SIZE=500 ile 2000 sayfa = 1M kayıt).
# EN: Schemathesis fuzz caught int64 overflow on unbounded skip. Cap at 1M
#     — far beyond any realistic pagination scenario.
MAX_SKIP = 1_000_000


@router.get(
    "/",
    response_model=list[SensorResponse],
    summary="Tüm sensörleri listele (skip + limit pagination)",
)
def get_all_sensors(
    skip: int = Query(default=0, ge=0, le=MAX_SKIP, description="Atlanacak kayıt sayısı (pagination offset, max 1M)"),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Sayfa boyutu (max 500)"),
    db: Session = Depends(get_db),
):
    return db.query(Sensor).order_by(Sensor.id).offset(skip).limit(limit).all()


@router.get(
    "/count",
    summary="Toplam sensör sayısı (pagination için)",
    description="Frontend slider'ının sayfa sayısını hesaplaması için kullanılır.",
)
def count_sensors(db: Session = Depends(get_db)) -> dict:
    return {"total": db.query(func.count(Sensor.id)).scalar() or 0}


@router.get(
    "/{sensor_id}",
    response_model=SensorResponse,
    summary="Tek bir sensörün detayı",
)
def get_sensor(sensor_id: int, db: Session = Depends(get_db)):
    sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor bulunamadi")
    return sensor


@router.post(
    "/",
    response_model=SensorResponse,
    status_code=201,
    dependencies=[Depends(verify_api_key)],
    summary="Yeni sensör ekle",
)
@limiter.limit(STRICT_RATE)
def create_sensor(request: Request, sensor: SensorCreate, db: Session = Depends(get_db)):
    db_sensor = Sensor(**sensor.model_dump())
    db.add(db_sensor)
    db.commit()
    db.refresh(db_sensor)
    return db_sensor


@router.delete(
    "/{sensor_id}",
    dependencies=[Depends(verify_api_key)],
    summary="Sensör sil",
)
@limiter.limit(STRICT_RATE)
def delete_sensor(request: Request, sensor_id: int, db: Session = Depends(get_db)):
    sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor bulunamadi")
    db.delete(sensor)
    db.commit()
    return {"message": "Sensor silindi"}


# ===== SENSOR READINGS =====
@router.post(
    "/readings",
    response_model=SensorReadingResponse,
    status_code=201,
    dependencies=[Depends(verify_api_key)],
    summary="Yeni sensör okuması kaydet",
)
@limiter.limit(STRICT_RATE)
def create_reading(request: Request, reading: SensorReadingCreate, db: Session = Depends(get_db)):
    db_reading = SoilMoistureReading(**reading.model_dump())
    db.add(db_reading)
    db.commit()
    db.refresh(db_reading)
    return db_reading


@router.get(
    "/{sensor_id}/readings",
    response_model=list[SensorReadingResponse],
    summary="Sensörün okumalarını listele",
)
def get_sensor_readings(sensor_id: int, limit: int = 50, db: Session = Depends(get_db)):
    return (
        db.query(SoilMoistureReading)
        .filter(SoilMoistureReading.sensor_id == sensor_id)
        .order_by(SoilMoistureReading.reading_timestamp.desc())
        .limit(limit)
        .all()
    )
