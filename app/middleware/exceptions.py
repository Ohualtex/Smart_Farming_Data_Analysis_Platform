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
from fastapi.responses import JSONResponse

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
            message=f"{resource} bulunamadi.",
            detail=detail,
        )


class UnauthorizedError(SFDAPError):
    """Kimlik doğrulama başarısız (401)."""

    error_code = "UNAUTHORIZED"
    status_code = 401

    def __init__(self, detail: str | None = None):
        super().__init__(
            message="Kimlik dogrulama basarisiz. Gecerli bir API anahtari gerekli.",
            detail=detail,
        )


class ForbiddenError(SFDAPError):
    """Yetkisiz erişim (403)."""

    error_code = "FORBIDDEN"
    status_code = 403

    def __init__(self, detail: str | None = None):
        super().__init__(
            message="Bu islemi gerceklestirmek icin yetkiniz yok.",
            detail=detail,
        )


class ValidationError(SFDAPError):
    """Validasyon hatası (422)."""

    error_code = "VALIDATION_ERROR"
    status_code = 422

    def __init__(self, message: str = "Gecersiz veri", detail: str | None = None):
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

    def __init__(self, service: str = "Dis servis", detail: str | None = None):
        super().__init__(
            message=f"{service} ile iletisim kurulamadi.",
            detail=detail,
        )


# ─── GLOBAL EXCEPTION HANDLER ───────────────────────────────────


def register_exception_handlers(app: FastAPI) -> None:
    """FastAPI uygulamasına global exception handler'ları kaydeder."""

    @app.exception_handler(SFDAPError)
    async def sfdap_exception_handler(request: Request, exc: SFDAPError):
        """Tüm SFDAP custom exception'larını yakalar."""
        status_code = getattr(exc, "status_code", 500)
        error_code = getattr(exc, "error_code", "INTERNAL_ERROR")

        return JSONResponse(
            status_code=status_code,
            content={
                "error_code": error_code,
                "message": exc.message,
                "detail": exc.detail,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Beklenmeyen hataları yakalar ve tutarlı format döndürür."""
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_ERROR",
                "message": "Beklenmeyen bir sunucu hatasi olustu.",
                "detail": str(exc) if exc.args else None,
            },
        )
