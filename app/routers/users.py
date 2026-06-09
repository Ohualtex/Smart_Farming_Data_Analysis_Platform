"""
Admin User Management Endpoints (REBUILD Faz 3.5)
===================================================
Admin-only kullanıcı yönetimi: listeleme, detay, oluşturma, şifre
sıfırlama, rol değiştirme ve silme.

Tüm endpoint'ler `admin` rolü gerektirir (`require_role("admin")`).
`password_hash` hiçbir response'ta expose edilmez.

Endpoints:
    GET    /api/auth/users              — tüm kullanıcıları listele
    GET    /api/auth/users/{id}         — tek kullanıcı detayı
    POST   /api/auth/users              — rol seçerek kullanıcı oluştur
    PATCH  /api/auth/users/{id}/role     — rol değiştir
    PATCH  /api/auth/users/{id}/password — şifre sıfırla
    DELETE /api/auth/users/{id}          — kullanıcı sil

---

Admin-only user management. Tüm endpoint'ler admin rolü gerektirir.
`auth.py`'den ayrıştırılmıştır (sorumluluk ayrımı).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import MAX_SQLITE_INT, get_db
from app.middleware.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.middleware.rate_limiter import AUTH_RATE, limiter
from app.models.models import Farm, User
from app.routers.auth import (
    CurrentUserResponse,
    PasswordChangeResponse,
    UserRole,
    _hash_password,
    require_role,
)
from app.schemas.schemas import UtcDateTime

router = APIRouter(prefix="/api/auth", tags=["Kullanıcı Yönetimi"])


# ─── Pydantic schemas ────────────────────────────────────────────────


class AdminUserListItem(BaseModel):
    """Admin kullanıcı listesi satırı — `password_hash` asla expose edilmez."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str
    phone: str | None = None
    created_at: UtcDateTime
    owned_farms_count: int = 0


class AdminUserCreateRequest(BaseModel):
    """Admin'in rol seçerek kullanıcı oluşturması — register'dan farkı: rol seçilebilir."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Yeni Çiftçi",
                "email": "yeni@ornek.com",
                "password": "GuvenliSifre2026",  # noqa: S106 — örnek, gerçek secret değil
                "role": "farmer",
                "phone": "05321234567",
            }
        }
    )

    name: str = Field(..., max_length=100)
    email: str = Field(..., max_length=150)
    password: str
    role: UserRole = "farmer"
    phone: str | None = Field(None, max_length=20)


class AdminPasswordResetRequest(BaseModel):
    """Admin'in bir kullanıcının şifresini sıfırlaması — current şifre istemez (override)."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"new_password": "YeniGecici2026"}}  # noqa: S106 — örnek
    )

    new_password: str


class UserRoleUpdateRequest(BaseModel):
    """Admin-only PATCH /users/{id}/role body — REBUILD Faz 1 / Adım 4."""

    model_config = ConfigDict(json_schema_extra={"example": {"role": "overseer"}})

    role: UserRole


# ─── Yardımcılar ─────────────────────────────────────────────────────


def _owned_farms_map(db: Session, user_ids: list[int]) -> dict[int, int]:
    """user_id → owned farm count map (tek group-by, N+1 önler)."""
    if not user_ids:
        return {}
    rows = db.query(Farm.user_id, func.count(Farm.id)).filter(Farm.user_id.in_(user_ids)).group_by(Farm.user_id).all()
    return dict(rows)


# ─── Endpoint'ler ────────────────────────────────────────────────────


@router.get(
    "/users",
    response_model=list[AdminUserListItem],
    summary="Tüm kullanıcıları listele (admin-only)",
    description=(
        "Sistemdeki tüm kullanıcıları döner — `role` ile filtrelenebilir, "
        "`skip`/`limit` ile sayfalanır. `password_hash` asla expose edilmez; "
        "`owned_farms_count` her kullanıcı için hesaplanır. Yalnız `admin`."
    ),
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Caller admin değil"},
    },
)
def list_users(
    role: UserRole | None = Query(default=None, description="Rol filtresi"),
    skip: int = Query(default=0, ge=0, le=MAX_SQLITE_INT),
    limit: int = Query(default=100, ge=1, le=500),
    _caller: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> list[AdminUserListItem]:
    """Tüm kullanıcılar (admin) — owned_farms_count tek group-by ile."""
    q = db.query(User)
    if role is not None:
        q = q.filter(User.role == role)
    users = q.order_by(User.id).offset(skip).limit(limit).all()
    farm_map = _owned_farms_map(db, [u.id for u in users])
    return [
        AdminUserListItem(
            id=u.id,
            name=u.name,
            email=u.email,
            role=u.role,
            phone=u.phone,
            created_at=u.created_at,
            owned_farms_count=farm_map.get(u.id, 0),
        )
        for u in users
    ]


@router.get(
    "/users/{user_id}",
    response_model=AdminUserListItem,
    summary="Tek kullanıcı detayı (admin-only)",
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Caller admin değil"},
        404: {"description": "Kullanıcı bulunamadı"},
    },
)
def get_user(
    user_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Hedef kullanıcı ID"),
    _caller: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminUserListItem:
    """Tek kullanıcının admin görünümü."""
    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        raise NotFoundError("Kullanıcı")
    owned = db.query(func.count(Farm.id)).filter(Farm.user_id == target.id).scalar() or 0
    return AdminUserListItem(
        id=target.id,
        name=target.name,
        email=target.email,
        role=target.role,
        phone=target.phone,
        created_at=target.created_at,
        owned_farms_count=owned,
    )


@router.post(
    "/users",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni kullanıcı oluştur — rol seçilebilir (admin-only)",
    description=(
        "Admin, rol belirterek (`farmer`/`developer`/`overseer`/`admin`) yeni "
        "kullanıcı oluşturur. Şifre bcrypt'le hash'lenir, min 8 karakter. "
        "Self-register'dan farkı: rol seçilebilir."
    ),
    responses={
        400: {"description": "Şifre 8 karakterden kısa"},
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Caller admin değil"},
        409: {"description": "E-posta zaten kayıtlı"},
    },
)
@limiter.limit(AUTH_RATE)
def admin_create_user(
    request: Request,
    payload: AdminUserCreateRequest,
    _caller: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> User:
    """Admin rol seçerek kullanıcı yaratır."""
    # Audit fix: e-posta normalize (strip + lower) — auth.register ile tutarlı;
    # case/whitespace varyantı mükerrer hesap yaratmasın, dup-check ile insert eşleşsin.
    email = payload.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise ConflictError(message="Bu e-posta zaten kayıtlı.")
    if len(payload.password) < 8:
        raise ValidationError(message="Şifre en az 8 karakter olmalı.")
    user = User(
        name=payload.name,
        email=email,
        password_hash=_hash_password(payload.password),
        role=payload.role,
        phone=payload.phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch(
    "/users/{user_id}/role",
    response_model=CurrentUserResponse,
    summary="Kullanıcı rolünü değiştir (admin-only)",
    description=(
        "Belirtilen kullanıcının `role`'ünü 4 değerli RBAC enum'undan birine çeker "
        "(`farmer` | `developer` | `overseer` | `admin`). Yalnız `admin` rolü çağırabilir. "
        "Admin kendi rolünü değiştiremez (lock-out koruması)."
    ),
    responses={
        400: {"description": "Geçersiz role değeri (Pydantic Literal validation)"},
        401: {"description": "Token eksik veya geçersiz"},
        403: {"description": "Caller admin değil"},
        404: {"description": "Hedef kullanıcı bulunamadı"},
        409: {"description": "Admin kendi rolünü değiştiremez (lock-out koruması)"},
    },
)
def update_user_role(
    payload: UserRoleUpdateRequest,
    user_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Hedef kullanıcı ID"),
    caller: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> CurrentUserResponse:
    """Hedef kullanıcının rolünü `payload.role` değerine çek."""
    if user_id == caller.id:
        raise ConflictError(
            message="Admin kendi rolünü değiştiremez (lock-out koruması). Başka bir admin promote/demote etmeli."
        )
    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        raise NotFoundError("Kullanıcı")
    target.role = payload.role
    db.commit()
    db.refresh(target)
    owned = db.query(func.count(Farm.id)).filter(Farm.user_id == target.id).scalar() or 0
    return CurrentUserResponse(
        id=target.id,
        name=target.name,
        email=target.email,
        role=target.role,
        phone=target.phone,
        owned_farms_count=owned,
    )


@router.patch(
    "/users/{user_id}/password",
    response_model=PasswordChangeResponse,
    summary="Kullanıcının şifresini sıfırla (admin-only)",
    description=(
        "Admin, hedef kullanıcının şifresini sıfırlar — mevcut şifre istenmez "
        "(override). Yeni şifre min 8 karakter. Kullanıcının aktif token'ları "
        "geçerli kalır (logout yapılmaz)."
    ),
    responses={
        400: {"description": "Yeni şifre 8 karakterden kısa"},
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Caller admin değil"},
        404: {"description": "Kullanıcı bulunamadı"},
    },
)
@limiter.limit(AUTH_RATE)
def admin_reset_password(
    request: Request,
    payload: AdminPasswordResetRequest,
    user_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Hedef kullanıcı ID"),
    _caller: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> PasswordChangeResponse:
    """Admin override — hedef kullanıcının şifresini sıfırla."""
    if len(payload.new_password) < 8:
        raise ValidationError(message="Yeni şifre en az 8 karakter olmalı.")
    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        raise NotFoundError("Kullanıcı")
    target.password_hash = _hash_password(payload.new_password)
    db.commit()
    return PasswordChangeResponse(detail="Sifre sifirlandi")


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Kullanıcı sil (admin-only)",
    description=(
        "Admin bir kullanıcıyı siler. Guard'lar: admin kendini silemez (409, "
        "lock-out koruması); çiftliği olan kullanıcı silinemez (409, yetim FK "
        "verisi önleme — önce çiftlikleri sil/devret)."
    ),
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Caller admin değil"},
        404: {"description": "Kullanıcı bulunamadı"},
        409: {"description": "Self-delete veya çiftliği olan kullanıcı"},
    },
)
def admin_delete_user(
    user_id: int = Path(..., ge=1, le=MAX_SQLITE_INT, description="Hedef kullanıcı ID"),
    caller: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> None:
    """Kullanıcı sil — self + farm-owner guard'larıyla."""
    if user_id == caller.id:
        raise ConflictError(message="Admin kendini silemez (lock-out koruması). Başka bir admin silmeli.")
    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        raise NotFoundError("Kullanıcı")
    farm_count = db.query(func.count(Farm.id)).filter(Farm.user_id == user_id).scalar() or 0
    if farm_count > 0:
        raise ConflictError(message=f"Bu kullanıcının {farm_count} çiftliği var; önce çiftlikleri sil veya devret.")
    db.delete(target)
    db.commit()
