"""
Request Logging Middleware
===========================
Her API isteğini loglar: endpoint, method, status code, süre, client IP.
Log formatı: [2026-04-20 15:30:00] GET /api/sensors/ 200 45ms 192.168.1.1

Mehmet Sait Tayşi — Cycle 5 Görevi
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Logger konfigürasyonu
logger = logging.getLogger("sfdap.access")
logger.setLevel(logging.INFO)

# Console handler (henüz yoksa ekle)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    Her gelen HTTP isteği için erişim logu oluşturur.

    Log bilgileri:
    - HTTP method (GET/POST/PUT/DELETE)
    - Endpoint path
    - HTTP status code
    - Response süresi (ms)
    - Client IP adresi
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()

        # Client IP — proxy arkasındaysa X-Forwarded-For kullan
        client_ip = request.headers.get(
            "x-forwarded-for",
            request.client.host if request.client else "unknown",
        )

        try:
            response = await call_next(request)
        except Exception:
            # Hata durumunda da logla
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "%s %s 500 %.0fms %s [ERROR]",
                request.method,
                request.url.path,
                duration_ms,
                client_ip,
            )
            raise

        # Başarılı response logu
        duration_ms = (time.perf_counter() - start_time) * 1000
        log_method = logger.warning if response.status_code >= 400 else logger.info

        log_method(
            "%s %s %d %.0fms %s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            client_ip,
        )

        return response
