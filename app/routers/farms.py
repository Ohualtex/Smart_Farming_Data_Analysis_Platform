"""
Farm Read-Only Endpoints — Cycle 9 prep + REBUILD Faz 1 RBAC
==============================================================
List + detail + per-farm soil analyses. RBAC kapsamı:
    farmer    → yalnız kendi çiftlikleri
    developer → tüm sistem (test/integration namespace)
    overseer  → tüm sistem read-only
    admin     → tüm sistem

Endpoints:
    GET /api/farms/                       — list (region/city filter + pagination)
    GET /api/farms/{farm_id}              — detail + nested fields
    GET /api/farms/{farm_id}/soil         — soil analyses across the farm's fields

Write operasyonları (POST/PATCH/DELETE) henüz yok — REBUILD Faz 4'te eylem
akışları ile gelecek.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session, selectinload

from app.database import MAX_SQLITE_INT, get_db
from app.middleware.rbac import assert_farm_ownership, scope_to_user
from app.models.models import Farm, Field, SoilAnalysis, User
from app.routers.auth import get_current_user_or_403
from app.schemas.schemas import FarmDetailResponse, FarmResponse, SoilAnalysisResponse

router = APIRouter(prefix="/api/farms", tags=["Çiftlik Yönetimi"])

# Pagination — same defaults as sensors/irrigation routers (see those
# modules for rationale on MAX_SKIP).
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500
MAX_SKIP = 1_000_000


@router.get(
    "/",
    response_model=list[FarmResponse],
    summary="Tüm çiftlikleri listele (rol-aware)",
    description=(
        "Farmer: yalnız kendi çiftlikleri. admin/overseer/developer: tüm sistem. "
        "Region (7 coğrafi bölge) ve city (il adı) ile filtrelenebilir; "
        "pagination `skip` + `limit` ile."
    ),
    responses={401: {"description": "Bearer token gerekli"}},
)
def list_farms(
    region: str | None = Query(default=None, description="Bölge filtresi (örn. 'Marmara', 'Akdeniz')"),
    city: str | None = Query(default=None, description="İl filtresi (örn. 'İstanbul', 'Antalya')"),
    skip: int = Query(default=0, ge=0, le=MAX_SKIP),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> list[Farm]:
    """Region/city filter + role-aware scope + sorted by id ascending."""
    q = scope_to_user(db.query(Farm), current_user, Farm.user_id)
    if region is not None:
        q = q.filter(Farm.region == region)
    if city is not None:
        q = q.filter(Farm.city == city)
    return q.order_by(Farm.id).offset(skip).limit(limit).all()


@router.get(
    "/{farm_id}",
    response_model=FarmDetailResponse,
    summary="Tek çiftliğin detayı (nested fields ile, rol-aware)",
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Farmer başkasının çiftliğine erişemez"},
        404: {"description": "Ciftlik bulunamadi"},
    },
)
def get_farm(
    farm_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Çiftlik ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> Farm:
    """selectinload ile N+1 önlenir; fields tek ek query'de yüklenir.

    Sahiplik kontrolü: farmer ise farm sahibi olmalı; değilse 403.
    admin/overseer/developer için sahiplik aranmaz.
    """
    assert_farm_ownership(db, farm_id, current_user)
    farm = db.query(Farm).options(selectinload(Farm.fields)).filter(Farm.id == farm_id).first()
    if not farm:
        # Theoretically unreachable — assert_farm_ownership zaten 404 fırlattı.
        # Defensive: race condition'da farm silinmiş olabilir.
        raise HTTPException(status_code=404, detail="Ciftlik bulunamadi")
    return farm


@router.get(
    "/{farm_id}/soil",
    response_model=list[SoilAnalysisResponse],
    summary="Çiftliğin tarlalarındaki toprak analizleri (rol-aware)",
    description=(
        "Çiftliğin tüm `Field`'larındaki `SoilAnalysis` kayıtlarını döner — "
        "tarih sırasıyla (en yeni önce). Farmer ise sahibi olmalı."
    ),
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Farmer başkasının çiftliğine erişemez"},
        404: {"description": "Ciftlik bulunamadi"},
    },
)
def get_farm_soil(
    farm_id: int = Path(..., ge=1, le=MAX_SQLITE_INT),
    skip: int = Query(default=0, ge=0, le=MAX_SKIP),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> list[SoilAnalysis]:
    # assert_farm_ownership hem 404 hem 403 kontrolünü yapar.
    assert_farm_ownership(db, farm_id, current_user)
    return (
        db.query(SoilAnalysis)
        .join(Field, SoilAnalysis.field_id == Field.id)
        .filter(Field.farm_id == farm_id)
        .order_by(SoilAnalysis.analysis_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
