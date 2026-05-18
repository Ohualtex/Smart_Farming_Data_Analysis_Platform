"""
Rate Limiting Middleware
==========================
SlowAPI-based request throttling.
- General endpoints: 100 req/min
- Auth endpoints: 30 req/min

---

SlowAPI tabanlı istek hız sınırlaması; genel uçlar 100/dk, auth 30/dk.
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
