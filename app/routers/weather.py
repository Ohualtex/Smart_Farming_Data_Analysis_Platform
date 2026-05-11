"""
Hava Durumu API Endpoint'leri
================================
Çiftlik bazlı hava durumu kayıtlarının CRUD işlemleri, dış API'den
(OpenWeatherMap) veri çekme ve veri temizleme pipeline'ı için endpoint'ler.

Ayşe Eslem Çekici & Mehmet Sait Tayşi — Cycle 4/5 Görevi
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import verify_api_key
from app.middleware.rate_limiter import AUTH_RATE, STRICT_RATE, limiter
from app.models.models import WeatherData
from app.schemas.schemas import WeatherDataCreate, WeatherDataResponse
from app.services.weather_service import weather_service

router = APIRouter(prefix="/api/weather", tags=["Hava Durumu"])


@router.get("/", response_model=list[WeatherDataResponse])
def get_weather_data(farm_id: int = None, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(WeatherData)
    if farm_id:
        query = query.filter(WeatherData.farm_id == farm_id)
    return query.order_by(WeatherData.recorded_at.desc()).limit(limit).all()


@router.post("/", response_model=WeatherDataResponse, status_code=201, dependencies=[Depends(verify_api_key)])
@limiter.limit(STRICT_RATE)
def create_weather_data(request: Request, data: WeatherDataCreate, db: Session = Depends(get_db)):
    db_weather = WeatherData(**data.model_dump())
    db.add(db_weather)
    db.commit()
    db.refresh(db_weather)
    return db_weather


@router.get("/latest/{farm_id}", response_model=WeatherDataResponse)
def get_latest_weather(farm_id: int, db: Session = Depends(get_db)):
    weather = (
        db.query(WeatherData).filter(WeatherData.farm_id == farm_id).order_by(WeatherData.recorded_at.desc()).first()
    )
    if not weather:
        raise HTTPException(status_code=404, detail="Hava durumu verisi bulunamadi")
    return weather


@router.post("/fetch/{farm_id}")
@limiter.limit(AUTH_RATE)
async def fetch_weather_from_api(
    request: Request,
    farm_id: int,
    lat: float = Query(..., description="Enlem"),
    lon: float = Query(..., description="Boylam"),
    db: Session = Depends(get_db),
):
    """
    OpenWeatherMap API'den anlık hava durumu verisini çeker,
    temizler ve veritabanına kaydeder.
    """
    try:
        raw_data = await weather_service.fetch_current_weather(lat, lon)
        record = weather_service.save_weather_record(db, farm_id, raw_data)
        return {
            "message": "Hava durumu verisi basariyla cekildi ve kaydedildi",
            "record_id": record.id,
            "data": {
                "temperature_c": record.temperature_c,
                "humidity_percent": record.humidity_percent,
                "precipitation_mm": record.precipitation_mm,
                "wind_speed_kmh": record.wind_speed_kmh,
            },
        }
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Dis API hatasi: {str(e)}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sunucu hatasi: {str(e)}") from e


@router.get("/stats/{farm_id}")
def get_weather_stats(
    farm_id: int,
    days: int = Query(default=7, ge=1, le=90, description="Son kac gun"),
    db: Session = Depends(get_db),
):
    """
    Belirli bir çiftliğin son N günlük hava durumu istatistiklerini döndürür.
    Ortalama, min, max sıcaklık, nem ve toplam yağış bilgilerini içerir.
    """
    return weather_service.get_weather_stats(db, farm_id, days)


@router.post("/clean")
@limiter.limit(STRICT_RATE)
def clean_weather_record(request: Request, data: dict):
    """
    Gönderilen hava durumu verisini temizler ve eksik alanları doldurur.
    Veri pipeline'ı test etmek için kullanılır.
    """
    cleaned = weather_service.clean_weather_data(data)
    filled = weather_service.fill_missing_fields(cleaned)
    return {
        "original": data,
        "cleaned": cleaned,
        "filled": filled,
    }
