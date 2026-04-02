from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.models import Sensor, SoilMoistureReading
from app.schemas.schemas import (
    SensorCreate, SensorResponse,
    SensorReadingCreate, SensorReadingResponse
)

router = APIRouter(prefix="/api/sensors", tags=["Sensor Verileri"])


@router.get("/", response_model=List[SensorResponse])
def get_all_sensors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Sensor).offset(skip).limit(limit).all()


@router.get("/{sensor_id}", response_model=SensorResponse)
def get_sensor(sensor_id: int, db: Session = Depends(get_db)):
    sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor bulunamadi")
    return sensor


@router.post("/", response_model=SensorResponse, status_code=201)
def create_sensor(sensor: SensorCreate, db: Session = Depends(get_db)):
    db_sensor = Sensor(**sensor.model_dump())
    db.add(db_sensor)
    db.commit()
    db.refresh(db_sensor)
    return db_sensor


@router.delete("/{sensor_id}")
def delete_sensor(sensor_id: int, db: Session = Depends(get_db)):
    sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor bulunamadi")
    db.delete(sensor)
    db.commit()
    return {"message": "Sensor silindi"}


# ===== SENSOR READINGS =====
@router.post("/readings", response_model=SensorReadingResponse, status_code=201)
def create_reading(reading: SensorReadingCreate, db: Session = Depends(get_db)):
    db_reading = SoilMoistureReading(**reading.model_dump())
    db.add(db_reading)
    db.commit()
    db.refresh(db_reading)
    return db_reading


@router.get("/{sensor_id}/readings", response_model=List[SensorReadingResponse])
def get_sensor_readings(sensor_id: int, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(SoilMoistureReading).filter(
        SoilMoistureReading.sensor_id == sensor_id
    ).order_by(SoilMoistureReading.reading_timestamp.desc()).limit(limit).all()
