"""
Sulama Optimizasyonu API Endpoint'leri
========================================
ML tabanlı sulama tahmini (RandomForest) ve sulama programı CRUD.

Miraç Duran — Cycle 4 Görevi
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import verify_api_key
from app.ml.irrigation_model import irrigation_optimizer
from app.models.models import IrrigationSchedule
from app.schemas.schemas import (
    IrrigationCreate,
    IrrigationPredictionRequest,
    IrrigationPredictionResponse,
    IrrigationResponse,
)

router = APIRouter(prefix="/api/irrigation", tags=["Sulama Optimizasyonu"])


@router.post(
    "/predict",
    response_model=IrrigationPredictionResponse,
    summary="ML sulama tahmini",
    description="Toprak nemi, sıcaklık, yağış gibi girdileri alıp önerilen "
    "su miktarını (litre) ve aciliyet seviyesini döndürür.",
)
def predict_irrigation(data: IrrigationPredictionRequest):
    return irrigation_optimizer.predict(
        soil_moisture=data.soil_moisture,
        soil_temperature=data.soil_temperature,
        humidity=data.humidity,
        temperature=data.temperature,
        precipitation=data.precipitation,
    )


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
