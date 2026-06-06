"""
Rate Limiting Middleware
==========================
SlowAPI-based request throttling (per-decorator; no global default_limits).
- Write (strict) endpoints: 30 req/min  (STRICT_RATE)
- Auth endpoints:          10 req/min  (AUTH_RATE)
- DEFAULT_RATE (100/min) is defined for convenience but not currently bound.

---

SlowAPI tabanlı istek hız sınırlaması (dekoratör bazlı; global default yok):
yazma uçları 30/dk (STRICT_RATE), auth uçları 10/dk (AUTH_RATE).
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


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
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
