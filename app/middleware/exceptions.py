"""
Custom Exceptions and Global Exception Handler
================================================
Returns a uniform error envelope for every API failure:
    {"error_code": "...", "message": "...", "detail": "..."}

---

Tüm API hataları için tutarlı response formatı sağlar.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.exc import IntegrityError

from app.config import settings

# ─── CUSTOM EXCEPTION SINIFLARI ─────────────────────────────────


class SFDAPError(Exception):
    """Tüm SFDAP hatalarının temel sınıfı."""

    def __init__(self, message: str = "Bilinmeyen hata", detail: str | None = None):
        self.message = message
        self.detail = detail
        super().__init__(self.message)


class NotFoundError(SFDAPError):
    """Kaynak bulunamadığında (404)."""

    error_code = "NOT_FOUND"
    status_code = 404

    def __init__(self, resource: str = "Kaynak", detail: str | None = None):
        super().__init__(
            message=f"{resource} bulunamadı.",
            detail=detail,
        )


class UnauthorizedError(SFDAPError):
    """Kimlik doğrulama başarısız (401)."""

    error_code = "UNAUTHORIZED"
    status_code = 401

    def __init__(self, detail: str | None = None):
        super().__init__(
            message="Kimlik doğrulama başarısız. Geçerli bir API anahtarı gerekli.",
            detail=detail,
        )


class ForbiddenError(SFDAPError):
    """Yetkisiz erişim (403)."""

    error_code = "FORBIDDEN"
    status_code = 403

    def __init__(self, detail: str | None = None):
        super().__init__(
            message="Bu işlemi gerçekleştirmek için yetkiniz yok.",
            detail=detail,
        )


class ValidationError(SFDAPError):
    """Manuel validasyon hatası (400 — kullanıcı girdisi business-rule ihlali).

    NOT: Pydantic schema validation 422 RequestValidationError handler'ında
    ele alınır; bu sınıf manuel `if x < 8: raise ValidationError(...)` gibi
    runtime kontrolleri için 400 döner (HTTPException(400) ile uyumlu).
    """

    error_code = "VALIDATION_ERROR"
    status_code = 400

    def __init__(self, message: str = "Geçersiz veri", detail: str | None = None):
        super().__init__(message=message, detail=detail)


class ConflictError(SFDAPError):
    """Kaynak çakışması (409) — ör. duplicate kayıt."""

    error_code = "CONFLICT"
    status_code = 409

    def __init__(self, message: str = "Kaynak zaten mevcut", detail: str | None = None):
        super().__init__(message=message, detail=detail)


class ExternalServiceError(SFDAPError):
    """Dış servis hatası (502) — ör. OpenWeatherMap API down."""

    error_code = "EXTERNAL_SERVICE_ERROR"
    status_code = 502

    def __init__(self, service: str = "Dış servis", detail: str | None = None):
        super().__init__(
            message=f"{service} ile iletişim kurulamadı.",
            detail=detail,
        )


# ─── GLOBAL EXCEPTION HANDLER ───────────────────────────────────


def register_exception_handlers(app: FastAPI) -> None:
    """FastAPI uygulamasına global exception handler'ları kaydeder."""

    @app.exception_handler(SFDAPError)
    async def sfdap_exception_handler(request: Request, exc: SFDAPError):
        """Tüm SFDAP custom exception'larını yakalar.

        Envelope: `{"error_code": "...", "message": "...", "detail": "..."}`.
        Backward compat (v4-6): exc.detail None ise `detail` alanı message ile
        doldurulur — eski HTTPException(detail="...") yanıtlarını bekleyen
        client'lar ve testler bozulmadan çalışır.
        """
        status_code = getattr(exc, "status_code", 500)
        error_code = getattr(exc, "error_code", "INTERNAL_ERROR")
        # detail None ise message'i fallback olarak koy (HTTPException uyumu)
        detail = exc.detail if exc.detail is not None else exc.message

        return JSONResponse(
            status_code=status_code,
            content={
                "error_code": error_code,
                "message": exc.message,
                "detail": detail,
            },
        )

    @app.exception_handler(IntegrityError)
    async def integrity_exception_handler(request: Request, exc: IntegrityError):
        """Map any SQLAlchemy IntegrityError (UNIQUE / FK violation) to 409.

        Without this the constraint violation surfaces as a 500 — the
        handler turns it into a documented client error.

        ---

        UNIQUE/FK ihlallerini 409 Conflict olarak normalize eder; aksi
        halde 500 olarak yansır ve client hatası gibi davranmaz.
        """
        # Ham DB hata metni (str(exc.orig)) tablo/kolon/constraint adlarını —
        # bazen değerleri — sızdırır → prod'da gizle, sunucuda logla (audit YÜKSEK).
        raw = str(exc.orig) if exc.orig else str(exc)
        logger.warning(f"IntegrityError: {raw}")
        return JSONResponse(
            status_code=409,
            content={
                "error_code": "CONFLICT",
                "message": "Veri çakışması: kayıt zaten mevcut veya ilişki kuralı ihlal edildi.",
                "detail": raw if settings.ENVIRONMENT != "production" else None,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError):
        """Pydantic request validation hatalarını döndürür.

        OpenAPI 422 sözleşmesini (`{"detail": [{"loc": [...], "msg": ..., "type": ...}]}`)
        koruyoruz — schemathesis conformance ve istemci kütüphane parser'larıyla
        uyumlu kalır. SFDAP envelope yalnızca SFDAPError/IntegrityError/Exception
        yollarında kullanılır (validation İngilizce kalır; frontend toast tarafı
        message map'leme yapar).
        """
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {
                        "loc": list(err.get("loc", [])),
                        "msg": err.get("msg", ""),
                        "type": err.get("type", ""),
                    }
                    for err in exc.errors()
                ],
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Beklenmeyen hataları yakalar ve tutarlı format döndürür.

        Ham exception metni (str(exc)) path/SQL/secret sızdırabilir → prod'da
        client'a dönmez, tam traceback sunucuda loglanır (audit YÜKSEK).
        """
        logger.exception(f"Beklenmeyen hata: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_ERROR",
                "message": "Beklenmeyen bir sunucu hatası oluştu.",
                "detail": (str(exc) if exc.args else None) if settings.ENVIRONMENT != "production" else None,
            },
        )
