"""
Sulama Optimizasyonu API Endpoint'leri
========================================
ML tabanlı sulama tahmini (RandomForest) ve sulama programı CRUD.

Miraç Duran — Cycle 4 Görevi
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query, Request
from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import verify_api_key
from app.middleware.rate_limiter import STRICT_RATE, limiter
from app.ml.irrigation_model import irrigation_optimizer
from app.models.models import IrrigationSchedule, ModelPerformanceLog
from app.schemas.schemas import (
    IrrigationCreate,
    IrrigationPredictionRequest,
    IrrigationPredictionResponse,
    IrrigationResponse,
)

# Pagination defaults — frontend slider 50'lik sayfalarla çalışıyor
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500
# shiftFinal Ayşe — Schemathesis fuzz tarafından yakalanan int64 overflow
# fix'i; sensors.py'deki MAX_SKIP ile aynı sebep (SQLite INTEGER).
# EN: Same int64 overflow fix as sensors.py — cap skip at 1M offset.
MAX_SKIP = 1_000_000

router = APIRouter(prefix="/api/irrigation", tags=["Sulama Optimizasyonu"])


def _log_prediction(db: Session, request: IrrigationPredictionRequest, result: dict) -> None:
    """ML tahmin log'unu sessiz şekilde DB'ye yaz; hata varsa istek akışını bozmaz."""
    try:
        log = ModelPerformanceLog(
            model_name="irrigation_rf",
            prediction_data=json.dumps(
                {
                    "input": request.model_dump(),
                    "output": result,
                },
                default=str,
            ),
        )
        db.add(log)
        db.commit()
    except Exception as exc:  # noqa: BLE001 — auto-log opsiyonel; istek başarılı olmalı
        logger.warning(f"Auto-log failed for irrigation prediction: {exc}")
        db.rollback()


@router.post(
    "/predict",
    response_model=IrrigationPredictionResponse,
    summary="ML sulama tahmini",
    description="Toprak nemi, sıcaklık, yağış gibi girdileri alıp önerilen "
    "su miktarını (litre) ve aciliyet seviyesini döndürür. Tahmin sonucu "
    "`ModelPerformanceLog` tablosuna otomatik kaydedilir (model_name='irrigation_rf').",
)
@limiter.limit(STRICT_RATE)
def predict_irrigation(request: Request, data: IrrigationPredictionRequest, db: Session = Depends(get_db)):
    result = irrigation_optimizer.predict(
        soil_moisture=data.soil_moisture,
        soil_temperature=data.soil_temperature,
        humidity=data.humidity,
        temperature=data.temperature,
        precipitation=data.precipitation,
    )
    _log_prediction(db, data, result)
    return result


@router.get(
    "/schedules",
    response_model=list[IrrigationResponse],
    summary="Sulama takvimini listele (skip + limit pagination)",
)
def get_schedules(
    field_id: int | None = Query(default=None, description="Belirli tarla için filtre"),
    skip: int = Query(default=0, ge=0, le=MAX_SKIP, description="Atlanacak kayıt sayısı (pagination offset, max 1M)"),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Sayfa boyutu (max 500)"),
    db: Session = Depends(get_db),
):
    query = db.query(IrrigationSchedule)
    if field_id:
        query = query.filter(IrrigationSchedule.field_id == field_id)
    return query.order_by(IrrigationSchedule.scheduled_date.desc()).offset(skip).limit(limit).all()


@router.get(
    "/schedules/count",
    summary="Toplam sulama programı sayısı (pagination için)",
    description="Frontend slider'ının sayfa sayısını hesaplaması için kullanılır. "
    "Opsiyonel `field_id` filtresi ile sayım yapılabilir.",
)
def count_schedules(
    field_id: int | None = Query(default=None, description="Belirli tarla için filtre"),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(func.count(IrrigationSchedule.id))
    if field_id:
        query = query.filter(IrrigationSchedule.field_id == field_id)
    return {"total": query.scalar() or 0}


@router.post(
    "/schedules",
    response_model=IrrigationResponse,
    status_code=201,
    dependencies=[Depends(verify_api_key)],
    summary="Yeni sulama programı oluştur",
)
@limiter.limit(STRICT_RATE)
def create_schedule(request: Request, schedule: IrrigationCreate, db: Session = Depends(get_db)):
    db_schedule = IrrigationSchedule(**schedule.model_dump())
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule
