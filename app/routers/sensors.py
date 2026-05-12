"""
Sensor API Endpoints
======================
CRUD for soil moisture / temperature sensors and their readings.
Write operations (POST/DELETE) require the X-API-Key header.

---

Toprak nem / sıcaklık sensörlerinin CRUD'u + okuma kayıtları.
Yazma uçları X-API-Key auth ister.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import MAX_SQLITE_INT, get_db
from app.middleware.auth import verify_api_key
from app.middleware.rate_limiter import STRICT_RATE, limiter
from app.models.models import Sensor, SoilMoistureReading
from app.schemas.schemas import SensorCreate, SensorReadingCreate, SensorReadingResponse, SensorResponse

router = APIRouter(prefix="/api/sensors", tags=["Sensör Verileri"])

# Pagination defaults — frontend pages through 50 records at a time.
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500
# 1M offset is far beyond any realistic pagination scenario; cap here
# avoids unbounded `skip` causing an int overflow on the DB binding.
# ---
# 1M offset gerçek pagination senaryosunun çok ötesinde; sınırsız `skip`
# DB binding'inde int overflow'a yol açar, bu sabit onu engeller.
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
    responses={404: {"description": "Sensor bulunamadı"}},
)
def get_sensor(
    sensor_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Sensor ID (max int64)"),
    db: Session = Depends(get_db),
):
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
def delete_sensor(
    request: Request,
    sensor_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Sensor ID (max int64)"),
    db: Session = Depends(get_db),
):
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
def get_sensor_readings(
    sensor_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Sensor ID (max int64)"),
    limit: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
):
    return (
        db.query(SoilMoistureReading)
        .filter(SoilMoistureReading.sensor_id == sensor_id)
        .order_by(SoilMoistureReading.reading_timestamp.desc())
        .limit(limit)
        .all()
    )
