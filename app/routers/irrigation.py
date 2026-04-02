from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.models import IrrigationSchedule
from app.schemas.schemas import (
    IrrigationCreate, IrrigationResponse,
    IrrigationPredictionRequest, IrrigationPredictionResponse
)
from app.ml.irrigation_model import irrigation_optimizer

router = APIRouter(prefix="/api/irrigation", tags=["Sulama Optimizasyonu"])


@router.post("/predict", response_model=IrrigationPredictionResponse)
def predict_irrigation(data: IrrigationPredictionRequest):
    result = irrigation_optimizer.predict(
        soil_moisture=data.soil_moisture,
        soil_temperature=data.soil_temperature,
        humidity=data.humidity,
        temperature=data.temperature,
        precipitation=data.precipitation,
    )
    return result


@router.get("/schedules", response_model=List[IrrigationResponse])
def get_schedules(field_id: int = None, limit: int = 20, db: Session = Depends(get_db)):
    query = db.query(IrrigationSchedule)
    if field_id:
        query = query.filter(IrrigationSchedule.field_id == field_id)
    return query.order_by(IrrigationSchedule.scheduled_date.desc()).limit(limit).all()


@router.post("/schedules", response_model=IrrigationResponse, status_code=201)
def create_schedule(schedule: IrrigationCreate, db: Session = Depends(get_db)):
    db_schedule = IrrigationSchedule(**schedule.model_dump())
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule
