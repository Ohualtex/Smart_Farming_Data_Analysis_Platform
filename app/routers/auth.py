"""
Kullanıcı Authentication Endpoint'leri — JWT + bcrypt
=======================================================
Cycle 7'de skeleton (sha256+salt + in-memory token dict) olarak başlayan
auth backend, Cycle 8'de production-grade JWT + bcrypt'e yükseltildi.

Bileşenler:
- **Şifre hash'leme**: `passlib[bcrypt]` ile bcrypt; her register'da otomatik salt.
- **Token üretimi**: `python-jose` ile HS256 imzalı JWT (`SECRET_KEY` ile).
  Payload: `{sub: user_id, iat, exp}`; varsayılan ömür `JWT_EXPIRE_HOURS` (24h).
- **Logout**: JWT stateless olduğundan logout'ta token'ı in-memory blacklist'e
  ekliyoruz; `/me` her istek başında blacklist kontrolü yapıyor. Production'da
  bu blacklist Redis veya DB'ye taşınmalı (multi-process / restart koruması).

Endpoint'ler:
    POST /api/auth/register  — yeni hesap (bcrypt hash)
    POST /api/auth/login     — JWT bearer token al
    GET  /api/auth/me        — token'la mevcut kullanıcı
    POST /api/auth/logout    — token'ı blacklist'e ekle (204)

EN: Cycle 8 production-grade auth — bcrypt password hashing + HS256 JWT
tokens, plus an in-memory blacklist for logout invalidation.

Miraç Duran — Cycle 8
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

# TODO Cycle 8+: pydantic[email] kurulduğunda EmailStr'e geç (email-validator gerekli)
from app.config import settings
from app.database import get_db
from app.middleware.rate_limiter import AUTH_RATE, STRICT_RATE, limiter
from app.models.models import User

router = APIRouter(prefix="/api/auth", tags=["Kimlik Doğrulama"])

# ─── Hash & token altyapısı ─────────────────────────────────────────
# bcrypt context — round count default 12; production'da yüksek
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT için stateless logout sağlayan in-memory blacklist.
# TODO Cycle 8+: production'da Redis (multi-process + restart koruması).
_BLACKLISTED_TOKENS: set[str] = set()


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
    email: str  # TODO Cycle 8+: EmailStr (pydantic[email])
    password: str  # min 8 karakter (validator alttaki register'da)
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
    """Yeni JWT üret — payload: sub, iat, exp. (token, expires_in_seconds) döner."""
    expire_delta = timedelta(hours=settings.JWT_EXPIRE_HOURS)
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + expire_delta).timestamp()),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, int(expire_delta.total_seconds())


def _decode_token(token: str) -> int:
    """JWT decode + sub'ı user_id olarak döndür. Geçersizse 401 fırlat."""
    if token in _BLACKLISTED_TOKENS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token iptal edildi")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gecersiz token") from exc
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


# ─── Endpoint'ler ────────────────────────────────────────────────────
@router.post(
    "/register",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni kullanıcı oluştur",
    description="Yeni hesap kaydı. Şifre bcrypt ile hash'lenir (Cycle 8'de sha256'dan bcrypt'e geçildi).",
)
@limiter.limit(AUTH_RATE)
def register(request: Request, payload: UserRegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu e-posta zaten kayitli")
    if len(payload.password) < 8:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Sifre en az 8 karakter olmali")
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
)
@limiter.limit(AUTH_RATE)
def login(request: Request, payload: UserLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not _verify_password(payload.password, user.password_hash or ""):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-posta veya sifre hatali")
    token, expires_in = _create_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Aktif kullanıcı bilgisi",
    description="`Authorization: Bearer <jwt>` header'ı ile çağrılır. JWT signature + exp + blacklist kontrol edilir.",
)
def me(user: User = Depends(_get_current_user)):
    return user


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
def logout(request: Request, authorization: str = Header(default="")):
    if authorization.startswith("Bearer "):
        token = authorization[7:]
        if token:
            _BLACKLISTED_TOKENS.add(token)
    return
