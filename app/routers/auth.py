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

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

# TODO: swap to EmailStr once pydantic[email] (email-validator) is installed.
from app.config import settings
from app.database import get_db
from app.middleware.exceptions import (
    ConflictError,
    ForbiddenError,
    UnauthorizedError,
    ValidationError,
)
from app.middleware.rate_limiter import AUTH_RATE, STRICT_RATE, limiter
from app.models.models import USER_ROLES, Farm, User  # USER_ROLES: tek kaynak referansı

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

# bcrypt algoritması parolayı 72 BYTE'ta sessizce keser (truncation). Audit
# fix (L3): bu sınırı aşan parolaları açıkça reddetmek için tek kaynak sabit.
_BCRYPT_MAX_BYTES = 72

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

    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=150)  # TODO: EmailStr (email-validator gerekli)
    password: str  # min 8 karakter (validator alttaki register'da)
    phone: str | None = Field(None, max_length=20)


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


# ─── Yardımcılar ─────────────────────────────────────────────────────
def _is_email_sane(email: str) -> bool:
    """Hafif e-posta sağlık kontrolü — EmailStr/email-validator yok.

    Audit fix (L1): en az 3 karakter, tam bir '@' ve '@'tan sonra bir '.'
    içermeli. Tam RFC doğrulaması değil; boş/sahte adresleri eler.
    EN: Lightweight email sanity check (no email-validator dependency).
    """
    if len(email) < 3 or email.count("@") != 1:
        return False
    local, _, domain = email.partition("@")
    return bool(local) and "." in domain and not domain.startswith(".") and not domain.endswith(".")


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
        # Audit fix (L2): exp + sub claim'leri zorunlu — exp'siz token süresiz
        # geçerli kalmasın, sub'suz token kimliksiz kabul edilmesin.
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except JWTError as exc:
        raise UnauthorizedError(detail="Geçersiz token.") from exc
    # jti blacklist kontrolü — payload.get çünkü eski (jti'siz) token'lara
    # tolerans (`jti` yoksa never-blacklisted sayılır; eski client'lar yeni
    # login alana kadar çalışmaya devam eder).
    jti = payload.get("jti")
    if jti is not None and jti in _BLACKLISTED_JTIS:
        raise UnauthorizedError(detail="Token iptal edildi.")
    sub = payload.get("sub")
    if sub is None:
        raise UnauthorizedError(detail="Token içeriği eksik.")
    try:
        return int(sub)
    except (TypeError, ValueError) as exc:
        raise UnauthorizedError(detail="Geçersiz token.") from exc


def _extract_bearer(authorization: str) -> str:
    """`Authorization: Bearer <token>` header'ından token'ı çıkar."""
    if not authorization.startswith("Bearer "):
        raise UnauthorizedError(detail="Token eksik.")
    return authorization[7:]


def _get_current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    """Bearer JWT'den kullanıcıyı çıkar; blacklist + signature + exp kontrolü."""
    token = _extract_bearer(authorization)
    user_id = _decode_token(token)
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise UnauthorizedError(detail="Kullanıcı bulunamadı.")
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
            raise ForbiddenError(detail=f"Bu işlem için yetki yok — gerekli rol(ler): {', '.join(sorted(allowed_set))}")
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
    # Audit fix: e-posta normalize (strip + lower) — case/whitespace varyantları
    # mükerrer hesap yaratmasın ve dup-check ile insert aynı değeri kullansın.
    email = payload.email.strip().lower()
    # Audit fix (L1): hafif e-posta sağlık kontrolü — email-validator/EmailStr
    # kurulu değil; en az '@' + '.' içermeli ve makul uzunlukta olmalı.
    if not _is_email_sane(email):
        raise ValidationError(message="Geçerli bir e-posta adresi girin.")
    # Audit fix (L4): şifre uzunluğu kontrolü dup-email kontrolünden ÖNCE çalışır
    # — geçersiz şifre 409 yerine 400 döner ve dup-check ile user enumeration azalır.
    if len(payload.password) < 8:
        # 400 — FastAPI'nin auto-generated 422 şeması list[ValidationError]
        # bekler; düz-string detail uyumsuz olur.
        # ---
        # 400 — FastAPI's auto-generated 422 schema expects
        # list[ValidationError]; a plain-string detail breaks it.
        raise ValidationError(message="Şifre en az 8 karakter olmalı.")
    # Audit fix (L3): bcrypt 72 BYTE'ta sessizce keser; açıkça reddet.
    if len(payload.password.encode("utf-8")) > _BCRYPT_MAX_BYTES:
        raise ValidationError(message=f"Şifre en fazla {_BCRYPT_MAX_BYTES} bayt olmalı.")
    if db.query(User).filter(User.email == email).first():
        raise ConflictError(message="Bu e-posta zaten kayıtlı.")
    user = User(
        name=payload.name,
        email=email,
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
    # Audit fix: register ile aynı normalize (strip + lower) — case/whitespace
    # varyantı login'i bloklamasın, stored e-posta ile eşleşsin.
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if user is None or not _verify_password(payload.password, user.password_hash or ""):
        raise UnauthorizedError(detail="E-posta veya şifre hatalı.")
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
        raise UnauthorizedError(detail="Mevcut şifre hatalı.")
    if len(payload.new_password) < 8:
        raise ValidationError(message="Yeni şifre en az 8 karakter olmalı.")
    # Audit fix (L3): bcrypt 72 BYTE'ta sessizce keser; açıkça reddet.
    if len(payload.new_password.encode("utf-8")) > _BCRYPT_MAX_BYTES:
        raise ValidationError(message=f"Yeni şifre en fazla {_BCRYPT_MAX_BYTES} bayt olmalı.")
    if payload.new_password == payload.current_password:
        raise ValidationError(message="Yeni şifre mevcut şifreyle aynı olamaz.")
    user.password_hash = _hash_password(payload.new_password)
    db.commit()
    return PasswordChangeResponse(detail="Sifre guncellendi")
