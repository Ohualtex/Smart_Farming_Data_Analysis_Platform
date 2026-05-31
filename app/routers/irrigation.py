"""
Irrigation Optimization API Endpoints — REBUILD Faz 4 RBAC + onay/status
==========================================================================
ML-driven irrigation prediction (RandomForest) plus RBAC-aware schedule CRUD.

REBUILD Faz 4: bu router Faz 1 RBAC migration'ından kaçmıştı — `POST /schedules`
eski `verify_api_key` (X-API-Key) kullanıyordu, `GET /schedules` auth'suzdu.
Şimdi tüm schedule endpoint'leri Bearer + 4-rol RBAC kapsamında:
    farmer    → yalnız kendi tarlalarının programları (Field → Farm → user_id)
    developer → tüm sistem (read-only)
    overseer  → tüm sistem (read-only)
    admin     → tüm sistem (read + write)
`POST /schedules` = "öneriyi onayla" (predict → schedule). `PATCH /schedules/{id}/status`
= durum takibi (pending → completed | cancelled). `POST /predict` public kalır
(stateless ML inference).
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Path, Query, Request
from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import MAX_SQLITE_INT, get_db
from app.middleware.exceptions import NotFoundError
from app.middleware.rate_limiter import STRICT_RATE, limiter
from app.middleware.rbac import _BYPASS_ROLES, assert_field_ownership, require_write
from app.ml.irrigation_model import irrigation_optimizer
from app.models.models import Farm, Field, IrrigationSchedule, ModelPerformanceLog, User
from app.routers.auth import get_current_user_or_403
from app.schemas.schemas import (
    IrrigationCreate,
    IrrigationPredictionRequest,
    IrrigationPredictionResponse,
    IrrigationResponse,
    IrrigationStatusUpdate,
)

# Pagination defaults — frontend pages through 50 records at a time.
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500
# Same int64 overflow guard as sensors.py — cap skip at 1M offset.
# ---
# sensors.py ile aynı int64 overflow koruması — skip 1M ile sınırlanır.
MAX_SKIP = 1_000_000

router = APIRouter(prefix="/api/irrigation", tags=["Sulama Optimizasyonu"])


def _scope_schedules_to_user(query, user: User):  # noqa: ANN001
    """IrrigationSchedule query'sini rol'e göre kapsamlandır.

    farmer: schedule → field → farm.user_id == user.id
    admin/overseer/developer: bypass (tüm sistem)
    """
    if user.role in _BYPASS_ROLES:
        return query
    return (
        query.join(Field, IrrigationSchedule.field_id == Field.id)
        .join(Farm, Field.farm_id == Farm.id)
        .filter(Farm.user_id == user.id)
    )


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
    responses={400: {"description": "Geçersiz JSON body"}},
)
@limiter.limit(STRICT_RATE)
def predict_irrigation(
    request: Request, data: IrrigationPredictionRequest, db: Session = Depends(get_db)
) -> IrrigationPredictionResponse:
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
    summary="Sulama takvimini listele (rol-aware, skip + limit pagination)",
    description="Farmer yalnız kendi tarlalarının programlarını görür; admin/overseer/developer tüm sistem.",
    responses={401: {"description": "Bearer token gerekli"}},
)
def get_schedules(
    field_id: int | None = Query(default=None, ge=1, le=MAX_SQLITE_INT, description="Belirli tarla için filtre"),
    skip: int = Query(default=0, ge=0, le=MAX_SKIP, description="Atlanacak kayıt sayısı (pagination offset, max 1M)"),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Sayfa boyutu (max 500)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> list[IrrigationSchedule]:
    query = _scope_schedules_to_user(db.query(IrrigationSchedule), current_user)
    if field_id:
        query = query.filter(IrrigationSchedule.field_id == field_id)
    return query.order_by(IrrigationSchedule.scheduled_date.desc()).offset(skip).limit(limit).all()


@router.get(
    "/schedules/count",
    summary="Toplam sulama programı sayısı (rol-aware, pagination için)",
    description="Frontend slider'ının sayfa sayısını hesaplaması için kullanılır. "
    "Farmer kendi kapsamında sayar; opsiyonel `field_id` filtresi.",
    responses={401: {"description": "Bearer token gerekli"}},
)
def count_schedules(
    field_id: int | None = Query(default=None, ge=1, le=MAX_SQLITE_INT, description="Belirli tarla için filtre"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> dict:
    query = _scope_schedules_to_user(db.query(func.count(IrrigationSchedule.id)), current_user)
    if field_id:
        query = query.filter(IrrigationSchedule.field_id == field_id)
    return {"total": query.scalar() or 0}


@router.post(
    "/schedules",
    response_model=IrrigationResponse,
    status_code=201,
    summary="Sulama önerisini onayla → program oluştur (rol-aware: farmer + admin)",
    description="ML önerisini (veya manuel) sulama programına dönüştürür. Farmer "
    "yalnız kendi tarlasına program ekleyebilir. overseer/developer yazamaz (403).",
    responses={
        400: {"description": "Geçersiz JSON body"},
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Yazma yetkisi yok veya başkasının tarlası"},
        404: {"description": "Tarla bulunamadı"},
    },
)
@limiter.limit(STRICT_RATE)
def create_schedule(
    request: Request,
    schedule: IrrigationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> IrrigationSchedule:
    """Öneriyi onayla: field ownership + write kontrolünden sonra schedule oluştur."""
    require_write(current_user)
    assert_field_ownership(db, schedule.field_id, current_user)
    db_schedule = IrrigationSchedule(**schedule.model_dump())
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule


@router.patch(
    "/schedules/{schedule_id}/status",
    response_model=IrrigationResponse,
    summary="Sulama programı durumunu güncelle (rol-aware: farmer + admin)",
    description="pending → completed (yapıldı) | cancelled (iptal). Farmer yalnız "
    "kendi tarlasının programını günceller.",
    responses={
        400: {"description": "Geçersiz status değeri"},
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Yazma yetkisi yok veya başkasının tarlası"},
        404: {"description": "Program bulunamadı"},
    },
)
@limiter.limit(STRICT_RATE)
def update_schedule_status(
    request: Request,
    payload: IrrigationStatusUpdate,
    schedule_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Sulama programı ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> IrrigationSchedule:
    """Sahiplik + write kontrolünden sonra durum güncelle."""
    require_write(current_user)
    schedule = db.query(IrrigationSchedule).filter(IrrigationSchedule.id == schedule_id).first()
    if schedule is None:
        raise NotFoundError("Sulama programı")
    # field ownership: schedule.field_id farmer'ın olmalı
    assert_field_ownership(db, schedule.field_id, current_user)
    schedule.status = payload.status
    db.commit()
    db.refresh(schedule)
    return schedule
