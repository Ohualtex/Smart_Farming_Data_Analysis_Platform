from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.models import WeatherData
from app.schemas.schemas import WeatherDataCreate, WeatherDataResponse

router = APIRouter(prefix="/api/weather", tags=["Hava Durumu"])


@router.get("/", response_model=List[WeatherDataResponse])
def get_weather_data(farm_id: int = None, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(WeatherData)
    if farm_id:
        query = query.filter(WeatherData.farm_id == farm_id)
    return query.order_by(WeatherData.recorded_at.desc()).limit(limit).all()


@router.post("/", response_model=WeatherDataResponse, status_code=201)
def create_weather_data(data: WeatherDataCreate, db: Session = Depends(get_db)):
    db_weather = WeatherData(**data.model_dump())
    db.add(db_weather)
    db.commit()
    db.refresh(db_weather)
    return db_weather


@router.get("/latest/{farm_id}", response_model=WeatherDataResponse)
def get_latest_weather(farm_id: int, db: Session = Depends(get_db)):
    weather = db.query(WeatherData).filter(
        WeatherData.farm_id == farm_id
    ).order_by(WeatherData.recorded_at.desc()).first()
    if not weather:
        raise HTTPException(status_code=404, detail="Hava durumu verisi bulunamadi")
    return weather
