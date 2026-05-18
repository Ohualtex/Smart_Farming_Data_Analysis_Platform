"""
Farm Read-Only Endpoints — Cycle 9 prep
========================================
List + detail + per-farm soil analyses. Read-only (GET) — write
operations (POST/PATCH/DELETE) deferred to post-Cycle-9 RBAC work.

Endpoints:
    GET /api/farms/                       — list (region/city filter + pagination)
    GET /api/farms/{farm_id}              — detail + nested fields
    GET /api/farms/{farm_id}/soil         — soil analyses across the farm's fields

---

Sadece okuma uçları — Cycle 9 öncesi schema-only kalan modellerden
`Farm` / `Field` / `SoilAnalysis` icin GET kapsamı. POST/PATCH/DELETE
RBAC çalışması Cycle 9 sonrasına ertelendi.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session, selectinload

from app.database import MAX_SQLITE_INT, get_db
from app.models.models import Farm, Field, SoilAnalysis
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
    summary="Tüm çiftlikleri listele",
    description=("Region (7 coğrafi bölge) ve city (81 il) ile filtrelenebilir; pagination `skip` + `limit` ile."),
)
def list_farms(
    region: str | None = Query(default=None, description="Bölge filtresi (örn. 'Marmara', 'Akdeniz')"),
    city: str | None = Query(default=None, description="İl filtresi (örn. 'İstanbul', 'Antalya')"),
    skip: int = Query(default=0, ge=0, le=MAX_SKIP),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
) -> list[Farm]:
    """Region/city filter + sorted by id ascending."""
    q = db.query(Farm)
    if region is not None:
        q = q.filter(Farm.region == region)
    if city is not None:
        q = q.filter(Farm.city == city)
    return q.order_by(Farm.id).offset(skip).limit(limit).all()


@router.get(
    "/{farm_id}",
    response_model=FarmDetailResponse,
    summary="Tek çiftliğin detayı (nested fields ile)",
    responses={404: {"description": "Ciftlik bulunamadi"}},
)
def get_farm(
    farm_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Çiftlik ID"),
    db: Session = Depends(get_db),
) -> Farm:
    """selectinload ile N+1 önlenir; fields tek ek query'de yüklenir."""
    farm = db.query(Farm).options(selectinload(Farm.fields)).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Ciftlik bulunamadi")
    return farm


@router.get(
    "/{farm_id}/soil",
    response_model=list[SoilAnalysisResponse],
    summary="Çiftliğin tarlalarındaki toprak analizleri",
    description=(
        "Çiftliğin tüm `Field`'larındaki `SoilAnalysis` kayıtlarını döner — "
        "tarih sırasıyla (en yeni önce). Çiftlik yoksa 404."
    ),
    responses={404: {"description": "Ciftlik bulunamadi"}},
)
def get_farm_soil(
    farm_id: int = Path(..., ge=1, le=MAX_SQLITE_INT),
    skip: int = Query(default=0, ge=0, le=MAX_SKIP),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
) -> list[SoilAnalysis]:
    # 404 önce — yoksa boş [] yerine açık hata.
    if not db.query(Farm.id).filter(Farm.id == farm_id).first():
        raise HTTPException(status_code=404, detail="Ciftlik bulunamadi")
    return (
        db.query(SoilAnalysis)
        .join(Field, SoilAnalysis.field_id == Field.id)
        .filter(Field.farm_id == farm_id)
        .order_by(SoilAnalysis.analysis_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
