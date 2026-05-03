"""
Sulama Optimizasyonu API Endpoint'leri
========================================
ML tabanlı sulama tahmini (RandomForest) ve sulama programı CRUD.

Miraç Duran — Cycle 4 Görevi
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import verify_api_key
from app.ml.irrigation_model import irrigation_optimizer
from app.models.models import IrrigationSchedule, ModelPerformanceLog
from app.schemas.schemas import (
    IrrigationCreate,
    IrrigationPredictionRequest,
    IrrigationPredictionResponse,
    IrrigationResponse,
)

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
def predict_irrigation(data: IrrigationPredictionRequest, db: Session = Depends(get_db)):
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
    summary="Sulama takvimini listele",
)
def get_schedules(field_id: int | None = None, limit: int = 20, db: Session = Depends(get_db)):
    query = db.query(IrrigationSchedule)
    if field_id:
        query = query.filter(IrrigationSchedule.field_id == field_id)
    return query.order_by(IrrigationSchedule.scheduled_date.desc()).limit(limit).all()


@router.post(
    "/schedules",
    response_model=IrrigationResponse,
    status_code=201,
    dependencies=[Depends(verify_api_key)],
    summary="Yeni sulama programı oluştur",
)
def create_schedule(schedule: IrrigationCreate, db: Session = Depends(get_db)):
    db_schedule = IrrigationSchedule(**schedule.model_dump())
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule
