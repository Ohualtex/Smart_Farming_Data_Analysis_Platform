"""
Rate Limiting Middleware
=========================
SlowAPI kullanarak API isteklerini sınırlandırır.
- Genel endpoint'ler: 100 istek/dakika
- Auth gerektiren endpoint'ler: 30 istek/dakika

Mehmet Sait Tayşi — Cycle 5 Görevi
"""

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse

# Client IP'ye göre rate limit
limiter = Limiter(key_func=get_remote_address)

# Varsayılan limitler
DEFAULT_RATE = "100/minute"
STRICT_RATE = "30/minute"
AUTH_RATE = "10/minute"


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Rate limit aşıldığında tutarlı hata formatı döndürür.
    HTTP 429 Too Many Requests.
    """
    return JSONResponse(
        status_code=429,
        content={
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": "Cok fazla istek gonderdiniz. Lutfen bekleyin.",
            "detail": str(exc.detail),
        },
    )
