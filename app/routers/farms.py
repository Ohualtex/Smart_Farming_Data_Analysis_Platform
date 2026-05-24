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

from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.database import MAX_SQLITE_INT, get_db
from app.middleware.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.middleware.rate_limiter import STRICT_RATE, limiter
from app.middleware.rbac import _WRITE_ROLES, assert_farm_ownership, scope_to_user
from app.models.models import Farm, Field, SoilAnalysis, User
from app.routers.auth import get_current_user_or_403
from app.schemas.schemas import (
    FarmCreate,
    FarmDetailResponse,
    FarmResponse,
    FarmUpdate,
    SoilAnalysisResponse,
)

router = APIRouter(prefix="/api/farms", tags=["Çiftlik Yönetimi"])

# Pagination — same defaults as sensors/irrigation routers (see those
# modules for rationale on MAX_SKIP).
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500
MAX_SKIP = 1_000_000


def _require_write(user: User) -> None:
    """overseer/developer için 403; farmer + admin OK (write set)."""
    if user.role not in _WRITE_ROLES:
        raise ForbiddenError(detail=f"Yazma yetkisi yok (rol: {user.role}); farmer veya admin gerek.")


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
        raise NotFoundError("Çiftlik")
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


# ─── WRITE (REBUILD Faz 4 — CRUD) ────────────────────────────────────
@router.post(
    "/",
    response_model=FarmResponse,
    status_code=201,
    summary="Yeni çiftlik oluştur (farmer + admin)",
    description="Çiftlik current_user adına oluşturulur (`user_id` body'de yok). overseer/developer yazamaz (403).",
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Yazma yetkisi yok (overseer/developer)"},
    },
)
@limiter.limit(STRICT_RATE)
def create_farm(
    request: Request,
    payload: FarmCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> Farm:
    """Çiftliği current_user sahipliğinde oluştur."""
    _require_write(current_user)
    farm = Farm(user_id=current_user.id, **payload.model_dump())
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


@router.patch(
    "/{farm_id}",
    response_model=FarmResponse,
    summary="Çiftliği güncelle (rol-aware: sahibi veya admin)",
    description="Partial update: yalnız verilen alanlar değişir (`exclude_unset`). "
    "Farmer yalnız kendi çiftliğini düzenleyebilir.",
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Yazma yetkisi yok veya başkasının çiftliği"},
        404: {"description": "Çiftlik bulunamadı"},
    },
)
@limiter.limit(STRICT_RATE)
def update_farm(
    request: Request,
    payload: FarmUpdate,
    farm_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Çiftlik ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> Farm:
    """Sahiplik + write kontrolünden sonra kısmi güncelleme."""
    _require_write(current_user)
    assert_farm_ownership(db, farm_id, current_user)
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        setattr(farm, field_name, value)
    db.commit()
    db.refresh(farm)
    return farm


@router.delete(
    "/{farm_id}",
    status_code=204,
    summary="Çiftliği sil (rol-aware: sahibi veya admin)",
    description="Tarlası olan çiftlik silinemez (409 — önce tarlaları sil). Yetim FK verisi önleme.",
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Yazma yetkisi yok veya başkasının çiftliği"},
        404: {"description": "Çiftlik bulunamadı"},
        409: {"description": "Çiftliğin tarlaları var (önce onları sil)"},
    },
)
@limiter.limit(STRICT_RATE)
def delete_farm(
    request: Request,
    farm_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Çiftlik ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> None:
    """Sahiplik + write + cascade-guard sonrası sil."""
    _require_write(current_user)
    assert_farm_ownership(db, farm_id, current_user)
    field_count = db.query(func.count(Field.id)).filter(Field.farm_id == farm_id).scalar() or 0
    if field_count > 0:
        raise ConflictError(message=f"Bu çiftliğin {field_count} tarlası var; önce tarlaları sil.")
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    db.delete(farm)
    db.commit()
