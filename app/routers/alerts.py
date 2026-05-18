"""
System Alert API Endpoints — REBUILD Faz 1 RBAC + is_resolved=None audit fix
=============================================================================
Sistem uyarıları için CRUD endpoint'leri: sensör anomalisi, hava
uyarısı, sistem hatası vb. listele/oluştur/çöz akışları.

RBAC kapsamı:
    farmer    → yalnız kendi farm'ına ait alert'ler
    developer → tüm sistem (test/integration)
    overseer  → tüm sistem read-only
    admin     → tüm sistem read + write

Audit bug fix (REBUILD Faz 1 / Adım 13):
    PATCH /alerts/{id} `is_resolved: None` payload'ı eski kod'da DB'ye
    NULL yazıyordu; SystemAlertResponse.is_resolved (bool) Pydantic
    validation 500 fırlatıyordu. Şimdi `model_dump(exclude_none=True)`
    ile None field'lar "no-op" sayılır — Schemathesis fuzz fail kapandı.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.orm import Session

from app.database import MAX_SQLITE_INT, get_db
from app.middleware.rate_limiter import STRICT_RATE, limiter
from app.middleware.rbac import _WRITE_ROLES, assert_farm_ownership
from app.models.models import Farm, SystemAlert, User
from app.routers.auth import get_current_user_or_403
from app.schemas.schemas import SystemAlertCreate, SystemAlertResponse, SystemAlertUpdate

router = APIRouter(prefix="/api/alerts", tags=["Sistem Uyarıları"])


def _require_write(user: User) -> None:
    """overseer/developer için 403; farmer + admin OK."""
    if user.role not in _WRITE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Yazma yetkisi yok (rol: {user.role}); farmer veya admin gerek",
        )


def _scope_alerts_to_user(query, user: User):  # noqa: ANN001
    """SystemAlert list'i rol'e göre kapsamlandır.

    farmer: alert.farm_id → farm.user_id == user.id (alert farm_id NULL ise
    sistem-wide alert; farmer bunları görmez)
    admin/overseer/developer: bypass
    """
    if user.role in ("admin", "overseer", "developer"):
        return query
    return query.join(Farm, SystemAlert.farm_id == Farm.id).filter(Farm.user_id == user.id)


@router.get(
    "/",
    response_model=list[SystemAlertResponse],
    summary="Sistem uyarılarını listele (rol-aware)",
    description=(
        "Farmer: yalnız kendi farm'larına bağlı alert'ler. "
        "Admin/overseer/developer: sistem-geneli. "
        "Severity ve resolved durumuna göre filtrelenebilir."
    ),
    responses={401: {"description": "Bearer token gerekli"}},
)
def list_alerts(
    severity: str | None = Query(default=None, description="Filtre: 'low' | 'medium' | 'critical'"),
    is_resolved: bool | None = Query(default=None, description="Filtre: çözüldü mü?"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> list[SystemAlert]:
    query = _scope_alerts_to_user(db.query(SystemAlert), current_user)
    if severity is not None:
        query = query.filter(SystemAlert.severity == severity)
    if is_resolved is not None:
        query = query.filter(SystemAlert.is_resolved == is_resolved)
    return query.order_by(SystemAlert.created_at.desc()).limit(limit).all()


@router.get(
    "/{alert_id}",
    response_model=SystemAlertResponse,
    summary="Tek bir uyarı getir (rol-aware)",
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Farmer başkasının alert'ine erişemez"},
        404: {"description": "Alert bulunamadı"},
    },
)
def get_alert(
    alert_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Alert ID (max int64)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> SystemAlert:
    alert = db.query(SystemAlert).filter(SystemAlert.id == alert_id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} bulunamadi")
    # Sahiplik check: farmer'lar yalnız kendi farm'larına ait alert'leri görsün.
    if current_user.role == "farmer":
        if alert.farm_id is None:
            # Sistem-wide alert (farm_id NULL) — farmer görmesin
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bu alert'e erisim yetkin yok")
        assert_farm_ownership(db, alert.farm_id, current_user)
    return alert


@router.post(
    "/",
    response_model=SystemAlertResponse,
    status_code=201,
    summary="Yeni uyarı oluştur (rol-aware: farmer + admin)",
    responses={
        400: {"description": "Geçersiz JSON body"},
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Yazma yetkisi yok veya farm sahibi değilsin"},
    },
)
@limiter.limit(STRICT_RATE)
def create_alert(
    request: Request,
    payload: SystemAlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> SystemAlert:
    _require_write(current_user)
    # Farmer farm_id verirse kendi farm'ı olmalı; None ise (system-wide alert)
    # yalnız admin yetkili — farmer bunu yapamaz.
    if payload.farm_id is not None:
        assert_farm_ownership(db, payload.farm_id, current_user)
    elif current_user.role == "farmer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Farmer sistem-wide alert (farm_id=None) oluşturamaz",
        )
    alert = SystemAlert(**payload.model_dump())
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.patch(
    "/{alert_id}",
    response_model=SystemAlertResponse,
    summary="Uyarıyı güncelle (rol-aware: farmer + admin)",
    description=(
        "Partial update: yalnız payload'da explicit verilen alanlar güncellenir. "
        "`is_resolved=None` / `severity=None` / `message=None` value'ları "
        "**no-op** sayılır (DB'ye NULL yazılmaz) — audit fix `5a48c21+`."
    ),
    responses={
        400: {"description": "Geçersiz JSON body"},
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Yazma yetkisi yok veya başkasının alert'i"},
        404: {"description": "Alert bulunamadı"},
    },
)
@limiter.limit(STRICT_RATE)
def update_alert(
    request: Request,
    payload: SystemAlertUpdate,
    alert_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Alert ID (max int64)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> SystemAlert:
    _require_write(current_user)
    alert = db.query(SystemAlert).filter(SystemAlert.id == alert_id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} bulunamadi")
    # Sahiplik check farmer için
    if current_user.role == "farmer":
        if alert.farm_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bu alert'e erisim yetkin yok")
        assert_farm_ownership(db, alert.farm_id, current_user)
    # ─── AUDIT FIX (REBUILD Faz 1 / Adım 13) ─────────────────────────
    # `exclude_none=True` → `is_resolved: None` / `severity: None` gibi
    # explicit None değerler DB'ye yazılmaz; partial update kontratı
    # "verilen alanlar" semantiğine sadık kalır. Önceden None DB'ye NULL
    # düşüyordu → response Pydantic (bool) → 500.
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in updates.items():
        setattr(alert, field, value)
    db.commit()
    db.refresh(alert)
    return alert
