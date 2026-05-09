"""
Kullanıcı Authentication Endpoint'leri — İskelet
==================================================
Mevcut API key bazlı auth'a ek olarak kullanıcı bazlı kimlik doğrulama.
Cycle 7'de Ecenur Üner'in Auth UI'ı bu backend'i çağıracak; Cycle 8'de
Miraç tarafından tam JWT + bcrypt ile production-grade'e çıkarılacak.

Mevcut durum (skeleton):
- /register: kullanıcı oluştur (sha256+salt ile şifre hash'le)
- /login: şifre doğrula → uuid token döndür (in-memory session)
- /me: token ile aktif kullanıcı bilgisi

Cycle 8 yükseltmesi (Miraç):
- bcrypt ile şifre hash'leme (`passlib[bcrypt]`)
- JWT token üretimi (`python-jose[cryptography]`)
- Refresh token + token expiry
- Role-based access control (RBAC) middleware
- /password-reset, /change-password, /verify-email akışları
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

# TODO Cycle 8: pydantic[email] kurulduğunda EmailStr'e geç (email-validator gerekli)
from app.database import get_db
from app.middleware.rate_limiter import AUTH_RATE, STRICT_RATE, limiter
from app.models.models import User

router = APIRouter(prefix="/api/auth", tags=["Kimlik Doğrulama"])

# ─── In-memory token store (skeleton — Cycle 8'de JWT'ye geçilir) ────
_TOKENS: dict[str, dict] = {}  # token → {user_id, created_at}
_TOKEN_TTL = timedelta(hours=24)


# ─── Pydantic schemas ────────────────────────────────────────────────
class UserRegisterRequest(BaseModel):
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
    email: str  # TODO Cycle 8: EmailStr (pydantic[email])
    password: str  # min 8 karakter (validator ekle Cycle 8)
    phone: str | None = None


class UserLoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "ahmet@ornek.com", "password": "GuvenliSifre2026"}}
    )

    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # saniye


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str


# ─── Yardımcılar ─────────────────────────────────────────────────────
def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """sha256+salt ile şifre hash'le (Cycle 8'de bcrypt'e geçilir)."""
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}${digest}", salt


def _verify_password(password: str, stored_hash: str) -> bool:
    """sha256+salt karşılaştırma."""
    try:
        salt, digest = stored_hash.split("$", 1)
        candidate = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        return secrets.compare_digest(candidate, digest)
    except (ValueError, AttributeError):
        return False


def _create_token(user_id: int) -> str:
    """In-memory random token üret (Cycle 8'de JWT)."""
    token = secrets.token_urlsafe(32)
    _TOKENS[token] = {"user_id": user_id, "created_at": datetime.now(UTC)}
    return token


def _get_current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    """Bearer token'dan kullanıcıyı çıkar."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token eksik")
    token = authorization[7:]
    session = _TOKENS.get(token)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gecersiz token")
    if datetime.now(UTC) - session["created_at"] > _TOKEN_TTL:
        del _TOKENS[token]
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token suresi doldu")
    user = db.query(User).filter(User.id == session["user_id"]).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kullanici bulunamadi")
    return user


# ─── Endpoint'ler ────────────────────────────────────────────────────
@router.post(
    "/register",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni kullanıcı oluştur",
    description="Yeni hesap kaydı. Şifre sha256+salt ile hash'lenir (Cycle 8'de bcrypt'e geçilecek).",
)
@limiter.limit(AUTH_RATE)
def register(request: Request, payload: UserRegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu e-posta zaten kayitli")
    if len(payload.password) < 8:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Sifre en az 8 karakter olmali")
    password_hash, _ = _hash_password(payload.password)
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=password_hash,
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
    summary="Giriş yap, token al",
    description="Doğru e-posta + şifre ile bearer token alınır. Token 24 saat geçerlidir.",
)
@limiter.limit(AUTH_RATE)
def login(request: Request, payload: UserLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not _verify_password(payload.password, user.password_hash or ""):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-posta veya sifre hatali")
    token = _create_token(user.id)
    return TokenResponse(access_token=token, expires_in=int(_TOKEN_TTL.total_seconds()))


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Aktif kullanıcı bilgisi",
    description="`Authorization: Bearer <token>` header'ı ile çağrılır. Aktif kullanıcının profilini döndürür.",
)
def me(user: User = Depends(_get_current_user)):
    return user


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Çıkış yap",
    description="Mevcut bearer token'ı iptal eder. Cycle 8'de JWT blacklist'e geçilir.",
)
@limiter.limit(STRICT_RATE)
def logout(request: Request, authorization: str = Header(default="")):
    if authorization.startswith("Bearer "):
        token = authorization[7:]
        _TOKENS.pop(token, None)
    return None
