"""
Weather API Endpoints — REBUILD Faz 1 RBAC
============================================
Çiftlik bazlı hava durumu CRUD'u + OpenWeatherMap fetch + temizleme.

RBAC kapsamı:
    farmer    → yalnız kendi çiftlikleri (read + write)
    developer → tüm sistem (test/integration); write OK
    overseer  → tüm sistem read-only (write 403)
    admin     → tüm sistem read + write

`POST /clean` stateless veri pipeline test endpoint'i — kimseye bağlı
veri yazmaz; auth zorunlu ama her rol kullanabilir.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.orm import Session

from app.database import MAX_SQLITE_INT, get_db
from app.middleware.exceptions import ExternalServiceError, ForbiddenError, NotFoundError, SFDAPError
from app.middleware.rate_limiter import AUTH_RATE, STRICT_RATE, limiter
from app.middleware.rbac import _WRITE_ROLES, assert_farm_ownership, scope_to_user
from app.models.models import User, WeatherData
from app.routers.auth import get_current_user_or_403
from app.schemas.schemas import WeatherDataCreate, WeatherDataResponse
from app.services.weather_service import weather_service

router = APIRouter(prefix="/api/weather", tags=["Hava Durumu"])


def _require_write(user: User) -> None:
    """overseer/developer için 403; farmer + admin OK."""
    if user.role not in _WRITE_ROLES:
        raise ForbiddenError(detail=f"Yazma yetkisi yok (rol: {user.role}); farmer veya admin gerek.")


@router.get(
    "/",
    response_model=list[WeatherDataResponse],
    summary="Hava durumu verileri (rol-aware)",
    responses={401: {"description": "Bearer token gerekli"}},
)
def get_weather_data(
    farm_id: int | None = Query(default=None, ge=1, le=MAX_SQLITE_INT, description="Farm ID filtresi"),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> list[WeatherData]:
    """Farmer: yalnız kendi farm'larındaki weather kayıtları.

    `farm_id` query verilince ayrıca o farm sahibi olunması doğrulanır
    (admin/overseer/developer bypass).
    """
    if farm_id is not None:
        assert_farm_ownership(db, farm_id, current_user)
        query = db.query(WeatherData).filter(WeatherData.farm_id == farm_id)
    else:
        # farmer için: yalnız kendi farms'a ait WeatherData
        # admin/overseer/developer: bypass (tüm kayıtlar)
        from app.models.models import Farm

        query = db.query(WeatherData)
        if current_user.role == "farmer":
            query = query.join(Farm, WeatherData.farm_id == Farm.id).filter(Farm.user_id == current_user.id)
        _ = scope_to_user  # imported but role-specific path above (intentional)
    return query.order_by(WeatherData.recorded_at.desc()).limit(limit).all()


@router.post(
    "/",
    response_model=WeatherDataResponse,
    status_code=201,
    summary="Yeni hava durumu kaydı (rol-aware: farmer + admin)",
    responses={
        400: {"description": "Geçersiz JSON body"},
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Yazma yetkisi yok veya farm sahibi değilsin"},
        404: {"description": "Farm bulunamadı"},
    },
)
@limiter.limit(STRICT_RATE)
def create_weather_data(
    request: Request,
    data: WeatherDataCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> WeatherData:
    _require_write(current_user)
    assert_farm_ownership(db, data.farm_id, current_user)
    db_weather = WeatherData(**data.model_dump())
    db.add(db_weather)
    db.commit()
    db.refresh(db_weather)
    return db_weather


@router.get(
    "/latest/{farm_id}",
    response_model=WeatherDataResponse,
    summary="Bir çiftliğin en son hava durumu kaydı (rol-aware)",
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Farmer başkasının farm'ına erişemez"},
        404: {"description": "Farm veya weather verisi bulunamadı"},
    },
)
def get_latest_weather(
    farm_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Farm ID (max int64)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> WeatherData:
    assert_farm_ownership(db, farm_id, current_user)
    weather = (
        db.query(WeatherData).filter(WeatherData.farm_id == farm_id).order_by(WeatherData.recorded_at.desc()).first()
    )
    if not weather:
        raise NotFoundError("Hava durumu verisi")
    return weather


@router.post(
    "/fetch/{farm_id}",
    summary="OpenWeatherMap'ten anlık veri çek (rol-aware: farmer + admin)",
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Yazma yetkisi yok veya farm sahibi değilsin"},
        404: {"description": "Farm bulunamadı"},
        502: {"description": "Dış API hatası"},
    },
)
@limiter.limit(AUTH_RATE)
async def fetch_weather_from_api(
    request: Request,
    farm_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Farm ID (max int64)"),
    lat: float = Query(..., description="Enlem"),
    lon: float = Query(..., description="Boylam"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> dict:
    """OpenWeatherMap'ten anlık veriyi çek + temizle + DB'ye kaydet.

    Farmer ise farm sahibi olmalı. Admin/developer bypass; overseer write
    yetkisi olmadığı için 403.
    """
    _require_write(current_user)
    assert_farm_ownership(db, farm_id, current_user)
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
        raise ExternalServiceError(service="OpenWeatherMap", detail=str(e)) from e
    except Exception as e:
        raise SFDAPError(message="Sunucu hatası oluştu.", detail=str(e)) from e


@router.get(
    "/stats/{farm_id}",
    summary="Çiftliğin son N günlük hava istatistikleri (rol-aware)",
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Farmer başkasının farm'ına erişemez"},
        404: {"description": "Farm bulunamadı"},
    },
)
def get_weather_stats(
    farm_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Farm ID (max int64)"),
    days: int = Query(default=7, ge=1, le=90, description="Son kac gun"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> dict:
    """Ortalama, min, max sıcaklık + nem + toplam yağış (Bearer + ownership)."""
    assert_farm_ownership(db, farm_id, current_user)
    return weather_service.get_weather_stats(db, farm_id, days)


@router.post(
    "/clean",
    summary="Hava verisi temizleme pipeline'ı (stateless, auth gerekli)",
    description=(
        "Gönderilen veriyi temizler + eksik alanları doldurur. DB'ye yazmaz; "
        "ham veri pipeline'ını test etmek için kullanılır. Her rol erişebilir."
    ),
    responses={401: {"description": "Bearer token gerekli"}},
)
@limiter.limit(STRICT_RATE)
def clean_weather_record(
    request: Request,
    data: dict,
    current_user: User = Depends(get_current_user_or_403),  # noqa: ARG001 — auth zorunlu, kullanım yok
) -> dict:
    """Stateless veri temizleme. Auth zorunlu ama rol-bağımsız."""
    cleaned = weather_service.clean_weather_data(data)
    filled = weather_service.fill_missing_fields(cleaned)
    return {
        "original": data,
        "cleaned": cleaned,
        "filled": filled,
    }
