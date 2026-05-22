"""
User Authentication Endpoints — JWT + bcrypt
==============================================
Production-grade auth: bcrypt password hashing, HS256 JWT tokens, and an
in-memory blacklist for logout invalidation.

Components:
- **Password hashing**: `passlib[bcrypt]`; salt generated per register.
- **Token issuance**: `python-jose` HS256 JWT signed with `SECRET_KEY`.
  Payload: `{sub: user_id, iat, exp}`; default TTL `JWT_EXPIRE_HOURS` (24h).
- **Logout**: since JWT is stateless, logout adds the token to an
  in-memory blacklist; `/me` checks the blacklist on every request.
  Production should move this blacklist to Redis or the DB for
  multi-process / restart safety.

Endpoints:
    POST /api/auth/register  — new account (bcrypt hash)
    POST /api/auth/login     — issue JWT bearer token
    GET  /api/auth/me        — current user from token
    POST /api/auth/logout    — blacklist the token (204)

---

Production-grade auth: bcrypt + HS256 JWT + in-memory logout blacklist.
Logout sonrası blacklist üretime alınınca Redis/DB'ye taşınmalı.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlalchemy.orm import Session

# TODO: swap to EmailStr once pydantic[email] (email-validator) is installed.
from app.config import settings
from app.database import MAX_SQLITE_INT, get_db
from app.middleware.rate_limiter import AUTH_RATE, STRICT_RATE, limiter
from app.models.models import USER_ROLES, Farm, User  # USER_ROLES: tek kaynak referansı
from app.schemas.schemas import UtcDateTime  # UTC-suffix'li date-time serializer (OpenAPI kontratı)

# Pydantic Literal alias — USER_ROLES (models.py) ile birebir eşleşmek zorunda.
# Schema validation ile DB CHECK constraint iki-katlı koruma: invalid rol
# 422 (Pydantic) veya 400 (HTTPException) ile reddedilir; DB seviyesine
# asla ulaşmaz.
UserRole = Literal["farmer", "developer", "overseer", "admin"]
# Runtime sanity-check: Literal değerleri USER_ROLES tuple'ı ile aynı kalmalı.
assert set(UserRole.__args__) == set(USER_ROLES), (  # noqa: S101
    "UserRole Literal ↔ USER_ROLES tuple sync bozuldu; iki tarafı da güncelle."
)

router = APIRouter(prefix="/api/auth", tags=["Kimlik Doğrulama"])

# ─── Hash & token altyapısı ─────────────────────────────────────────
# bcrypt context — round count default 12; production'da yüksek
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT için stateless logout sağlayan in-memory blacklist.
# `jti` (JWT ID, RFC 7519 §4.1.7) üzerinden çalışır — aynı kullanıcının aynı
# saniyede aldığı iki token'ın `sub`+`iat`+`exp` payload'ı identical olabilir
# ve token-string-eşleşmesi cross-contamination yaratırdı. `jti` her token
# için benzersiz UUID (`uuid4().hex`).
# TODO: move to Redis or DB in production (multi-process + restart safe).
_BLACKLISTED_JTIS: set[str] = set()


# ─── Pydantic schemas ────────────────────────────────────────────────
class UserRegisterRequest(BaseModel):
    """Registration payload — name, email, password (min 8 chars), optional phone."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Ahmet Yılmaz",
                "email": "ahmet@ornek.com",
                "password": "GuvenliSifre2026",
                "phone": "05321234567",
            }
        }
    )

    name: str
    email: str  # TODO: switch to EmailStr once pydantic[email] is in.
    password: str  # min 8 karakter (validator alttaki register'da)
    phone: str | None = None


class UserLoginRequest(BaseModel):
    """Login payload — email + password."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "ahmet@ornek.com", "password": "GuvenliSifre2026"}}
    )

    email: str
    password: str


class TokenResponse(BaseModel):
    """JWT bearer token + expiry in seconds."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # saniye


class CurrentUserResponse(BaseModel):
    """Authenticated user profile — emitted by `/api/auth/me` ve role promotion.

    REBUILD Faz 1 / Adım 5: `phone` + `owned_farms_count` eklendi. Frontend
    "Hesabım" sayfası bu sayıyı kart başlığında gösterecek.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str
    phone: str | None = None
    # Caller'a ait `Farm` sayısı — `/me` endpoint'inde hesaplanır.
    # Role promotion endpoint'i (`PATCH /users/{id}/role`) hedef
    # kullanıcının çiftliklerini sayar (admin için bilgi amaçlı).
    owned_farms_count: int = 0


class UserRoleUpdateRequest(BaseModel):
    """Admin-only PATCH /users/{id}/role body — REBUILD Faz 1 / Adım 4."""

    model_config = ConfigDict(json_schema_extra={"example": {"role": "overseer"}})

    role: UserRole


class PasswordChangeRequest(BaseModel):
    """PATCH /me/password body — REBUILD Faz 2 / Adım 9.

    Mevcut şifre doğrulaması zorunlu (saldırgan ele geçirdiği bir token'la
    yeni şifre koyamasın). `new_password` 8 char min (register ile aynı kural).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_password": "EskiSifre2026",  # noqa: S105 — örnek, gerçek secret değil
                "new_password": "YeniSifre2026",  # noqa: S105
            }
        }
    )

    current_password: str
    new_password: str


class PasswordChangeResponse(BaseModel):
    """Şifre değişikliği başarı yanıtı."""

    detail: str = "Sifre guncellendi"


# ─── Admin kullanıcı yönetimi şemaları (REBUILD Faz 3.5) ──────────────
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

    name: str
    email: str
    password: str
    role: UserRole = "farmer"
    phone: str | None = None


class AdminPasswordResetRequest(BaseModel):
    """Admin'in bir kullanıcının şifresini sıfırlaması — current şifre istemez (override)."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"new_password": "YeniGecici2026"}}  # noqa: S106 — örnek
    )

    new_password: str


# ─── Yardımcılar ─────────────────────────────────────────────────────
def _hash_password(password: str) -> str:
    """bcrypt hash üret — `pwd_context` her seferinde yeni salt kullanır.

    EN: Returns a bcrypt hash; passlib generates a fresh salt per call.
    """
    return pwd_context.hash(password)


def _verify_password(password: str, stored_hash: str) -> bool:
    """bcrypt karşılaştırma; stored_hash boş veya bozuksa False döner.

    EN: Constant-time bcrypt verification; tolerant of empty/legacy hashes.
    """
    if not stored_hash:
        return False
    try:
        return pwd_context.verify(password, stored_hash)
    except (ValueError, TypeError):
        # bcrypt formatında değil (eski sha256$digest veya bozuk) → reddet
        return False


def _create_token(user_id: int) -> tuple[str, int]:
    """Yeni JWT üret — payload: sub, iat, exp, jti. (token, expires_in_seconds) döner."""
    expire_delta = timedelta(hours=settings.JWT_EXPIRE_HOURS)
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + expire_delta).timestamp()),
        # jti: token başına benzersiz ID — blacklist `jti` ile çalışır
        # (token-string yerine), aynı saniye + aynı user collision'ından korur.
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, int(expire_delta.total_seconds())


def _decode_token(token: str) -> int:
    """JWT decode + sub'ı user_id olarak döndür. Geçersizse 401 fırlat."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gecersiz token") from exc
    # jti blacklist kontrolü — payload.get çünkü eski (jti'siz) token'lara
    # tolerans (`jti` yoksa never-blacklisted sayılır; eski client'lar yeni
    # login alana kadar çalışmaya devam eder).
    jti = payload.get("jti")
    if jti is not None and jti in _BLACKLISTED_JTIS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token iptal edildi")
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token icerigi eksik")
    try:
        return int(sub)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gecersiz token") from exc


def _extract_bearer(authorization: str) -> str:
    """`Authorization: Bearer <token>` header'ından token'ı çıkar."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token eksik")
    return authorization[7:]


def _get_current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    """Bearer JWT'den kullanıcıyı çıkar; blacklist + signature + exp kontrolü."""
    token = _extract_bearer(authorization)
    user_id = _decode_token(token)
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kullanici bulunamadi")
    return user


# ─── Public dependency aliases (REBUILD Faz 1 / Adım 3) ─────────────
# Diğer router'lar (`farms`, `sensors`, ...) bunları import edip
# `Depends(get_current_user_or_403)` / `Depends(require_role('admin'))`
# şeklinde kullanır. `_get_current_user` private alias olarak modül-içi
# kullanım için bırakıldı (mevcut /me, /logout endpoint'leri ona bağlı).

get_current_user_or_403 = _get_current_user
"""Bearer JWT zorunlu — write endpoint'ler için. Geçersizse 401."""


def current_user_optional(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> User | None:
    """Bearer JWT varsa user döner, yoksa `None` — public read endpoint'ler için.

    Token geçersiz/expired/blacklisted ise sessizce `None` döner;
    endpoint'e "anonim erişim" semantiği verir (örn. dashboard public
    sayfaları).
    """
    if not authorization.startswith("Bearer "):
        return None
    try:
        return _get_current_user(authorization=authorization, db=db)
    except HTTPException:
        return None


def require_role(*allowed_roles: str) -> Callable[..., User]:
    """Endpoint'i belirtilen rollere kısıtlayan dependency factory.

    Kullanım:
        # tek rol — admin-only endpoint
        @router.delete(..., dependencies=[Depends(require_role("admin"))])

        # birden fazla rol — farmer veya admin
        def endpoint(user: User = Depends(require_role("farmer", "admin"))):
            ...

    Geçersiz token → 401 (get_current_user_or_403'ten).
    Yetersiz rol → 403 (`{allowed_roles}` listesi error detail'inde).
    """
    if not allowed_roles:
        raise ValueError("require_role en az bir rol almak zorunda")
    allowed_set = set(allowed_roles)

    def _dep(user: User = Depends(_get_current_user)) -> User:
        if user.role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Bu islem icin yetki yok — gerekli rol(ler): {', '.join(sorted(allowed_set))}",
            )
        return user

    return _dep


# ─── Endpoint'ler ────────────────────────────────────────────────────
@router.post(
    "/register",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni kullanıcı oluştur",
    description="Yeni hesap kaydı. Şifre bcrypt ile hash'lenir.",
    responses={
        400: {"description": "Geçersiz JSON body"},
        409: {"description": "E-posta zaten kayıtlı"},
    },
)
@limiter.limit(AUTH_RATE)
def register(request: Request, payload: UserRegisterRequest, db: Session = Depends(get_db)) -> User:
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu e-posta zaten kayitli")
    if len(payload.password) < 8:
        # 400 — FastAPI'nin auto-generated 422 şeması list[ValidationError]
        # bekler; düz-string detail uyumsuz olur.
        # ---
        # 400 — FastAPI's auto-generated 422 schema expects
        # list[ValidationError]; a plain-string detail breaks it.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sifre en az 8 karakter olmali")
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=_hash_password(payload.password),
        role="farmer",
        phone=payload.phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Giriş yap, JWT bearer token al",
    description=(
        "Doğru e-posta + şifre ile HS256 imzalı JWT bearer token alınır. "
        "Token varsayılan 24 saat geçerlidir (`JWT_EXPIRE_HOURS` ile ayarlanabilir)."
    ),
    responses={
        400: {"description": "Geçersiz JSON body"},
        401: {"description": "E-posta veya şifre hatalı"},
    },
)
@limiter.limit(AUTH_RATE)
def login(request: Request, payload: UserLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not _verify_password(payload.password, user.password_hash or ""):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-posta veya sifre hatali")
    token, expires_in = _create_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Aktif kullanıcı bilgisi",
    description=(
        "`Authorization: Bearer <jwt>` header'ı ile çağrılır. JWT signature + exp + "
        "blacklist kontrol edilir. Yanıt `owned_farms_count` (caller'a ait çiftlik "
        "sayısı) içerir — frontend 'Hesabım' sayfası için (REBUILD Faz 1 / Adım 5)."
    ),
    responses={
        401: {"description": "Token eksik, süresi dolmuş ya da blacklist'te"},
    },
)
def me(
    user: User = Depends(_get_current_user),
    db: Session = Depends(get_db),
) -> CurrentUserResponse:
    """Caller'ın profil bilgisi + sahip olunan çiftlik sayısı."""
    owned = db.query(func.count(Farm.id)).filter(Farm.user_id == user.id).scalar() or 0
    return CurrentUserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        phone=user.phone,
        owned_farms_count=owned,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Çıkış yap",
    description=(
        "Mevcut bearer JWT'yi blacklist'e ekler — sonraki istekler 401 döner. "
        "Production'da bu blacklist Redis'e taşınmalı (multi-process / restart koruması)."
    ),
)
@limiter.limit(STRICT_RATE)
def logout(request: Request, authorization: str = Header(default="")) -> None:
    if authorization.startswith("Bearer "):
        token = authorization[7:]
        if token:
            # Decode et, jti'yi al, blacklist'e ekle. Decode hatası logout'u
            # 204 sessiz başarıya çevirmez — best-effort (idempotent kontrat).
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            except JWTError:
                return  # Bozuk/expired token zaten geçersiz — ek iş yok.
            jti = payload.get("jti")
            if jti:
                _BLACKLISTED_JTIS.add(jti)
    return


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
        # Admin self-demotion → potansiyel lock-out (son admin kendini farmer
        # yaparsa promotion endpoint'i çağıracak admin kalmaz).
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin kendi rolünü değiştiremez (lock-out koruması). Başka bir admin promote/demote etmeli.",
        )
    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanici bulunamadi")
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
    "/me/password",
    response_model=PasswordChangeResponse,
    summary="Kendi şifreni değiştir",
    description=(
        "Authenticated kullanıcının şifresini günceller. `current_password` doğrulanır "
        "(saldırgan ele geçirdiği token'la yeni şifre koyamasın). `new_password` minimum "
        "8 karakter. Mevcut tüm aktif token'lar yine geçerli kalır (logout yapılmaz); "
        "frontend bir sonraki adımda kullanıcıdan re-login isteyebilir."
    ),
    responses={
        400: {"description": "Yeni şifre 8 karakterden kısa"},
        401: {"description": "Token eksik veya current_password hatalı"},
    },
)
@limiter.limit(AUTH_RATE)
def change_password(
    request: Request,
    payload: PasswordChangeRequest,
    user: User = Depends(_get_current_user),
    db: Session = Depends(get_db),
) -> PasswordChangeResponse:
    """Mevcut şifreyi doğrula, yenisini bcrypt ile hash'le, DB'ye kaydet."""
    if not _verify_password(payload.current_password, user.password_hash or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mevcut sifre hatali",
        )
    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Yeni sifre en az 8 karakter olmali",
        )
    if payload.new_password == payload.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Yeni sifre mevcut sifreyle ayni olamaz",
        )
    user.password_hash = _hash_password(payload.new_password)
    db.commit()
    return PasswordChangeResponse(detail="Sifre guncellendi")


# ─── ADMIN KULLANICI YÖNETİMİ (REBUILD Faz 3.5) ──────────────────────
# Tüm endpoint'ler admin-only (require_role("admin") → 403/401). Mevcut
# `/api/auth/users/{id}/role` ile aynı namespace; tag "Kullanıcı Yönetimi".


def _owned_farms_map(db: Session, user_ids: list[int]) -> dict[int, int]:
    """user_id → owned farm count map (tek group-by, N+1 önler)."""
    if not user_ids:
        return {}
    rows = db.query(Farm.user_id, func.count(Farm.id)).filter(Farm.user_id.in_(user_ids)).group_by(Farm.user_id).all()
    return dict(rows)


@router.get(
    "/users",
    response_model=list[AdminUserListItem],
    tags=["Kullanıcı Yönetimi"],
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
    tags=["Kullanıcı Yönetimi"],
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanici bulunamadi")
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
    tags=["Kullanıcı Yönetimi"],
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
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu e-posta zaten kayitli")
    if len(payload.password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sifre en az 8 karakter olmali")
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=_hash_password(payload.password),
        role=payload.role,
        phone=payload.phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch(
    "/users/{user_id}/password",
    response_model=PasswordChangeResponse,
    tags=["Kullanıcı Yönetimi"],
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Yeni sifre en az 8 karakter olmali")
    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanici bulunamadi")
    target.password_hash = _hash_password(payload.new_password)
    db.commit()
    return PasswordChangeResponse(detail="Sifre sifirlandi")


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Kullanıcı Yönetimi"],
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
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin kendini silemez (lock-out koruması). Başka bir admin silmeli.",
        )
    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanici bulunamadi")
    farm_count = db.query(func.count(Farm.id)).filter(Farm.user_id == user_id).scalar() or 0
    if farm_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Bu kullanicinin {farm_count} ciftligi var; once ciftlikleri sil veya devret.",
        )
    db.delete(target)
    db.commit()
