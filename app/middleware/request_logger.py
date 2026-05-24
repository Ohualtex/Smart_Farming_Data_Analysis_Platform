"""
Request Logging Middleware
===========================
Logs every API request (endpoint, method, status, duration, client IP)
and attaches a UUID `request_id` to each one. The id is exposed via the
`X-Request-ID` response header and bound to the loguru context so every
downstream log record inherits it (trace propagation for structured
logging).

Log format: `[2026-04-20 15:30:00] GET /api/sensors/ 200 45ms 192.168.1.1 [req-id=abc]`

---

Her isteğe UUID request_id atanır, X-Request-ID header'ına yazılır ve
loguru context'ine bind edilerek tüm child log kayıtlarına yayılır.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from loguru import logger as loguru_logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

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

# İstemci kendi request ID'sini gönderebilir (dağıtık trace için)
INCOMING_REQUEST_ID_HEADER = "x-request-id"
OUTGOING_REQUEST_ID_HEADER = "X-Request-ID"


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    Her gelen HTTP isteği için erişim logu oluşturur ve request_id propagate eder.

    Log bilgileri:
    - HTTP method (GET/POST/PUT/DELETE)
    - Endpoint path
    - HTTP status code
    - Response süresi (ms)
    - Client IP adresi
    - Request ID (UUID, trace correlation için)
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Attach a request_id, log the result, and emit `X-Request-ID`."""
        start_time = time.perf_counter()

        # İstemci kendi request_id'sini gönderdiyse onu kullan; yoksa yeni UUID üret.
        # Dağıtık sistemlerde upstream service'in ID'sini korumak iyi pratik.
        # EN: Honour client-provided X-Request-ID if present; otherwise generate.
        request_id = request.headers.get(INCOMING_REQUEST_ID_HEADER) or uuid.uuid4().hex

        # Client IP — proxy arkasındaysa X-Forwarded-For kullan
        client_ip = request.headers.get(
            "x-forwarded-for",
            request.client.host if request.client else "unknown",
        )

        # Loguru context'ine request_id bind et — alt çağrılar otomatik propagate alır.
        # JSON formatter'da `extra.request_id` olarak görünür.
        with loguru_logger.contextualize(request_id=request_id, client_ip=client_ip):
            try:
                response = await call_next(request)
            except Exception:
                # Hata durumunda traceback ile logla (logger.exception)
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.exception(
                    "%s %s 500 %.0fms %s [req-id=%s] [ERROR]",
                    request.method,
                    request.url.path,
                    duration_ms,
                    client_ip,
                    request_id,
                )
                raise

            # Başarılı response logu
            duration_ms = (time.perf_counter() - start_time) * 1000
            # Slow request → WARN (perf gözlemi); >=400 status → WARN; aksi INFO
            slow_threshold = settings.LOG_SLOW_REQUEST_MS
            is_slow = duration_ms >= slow_threshold
            log_method = logger.warning if response.status_code >= 400 or is_slow else logger.info
            slow_tag = " [SLOW]" if is_slow else ""
            log_method(
                "%s %s %d %.0fms %s [req-id=%s]%s",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                client_ip,
                request_id,
                slow_tag,
            )

            # Response header'a request_id ekle (istemci trace ile eşleştirebilsin)
            response.headers[OUTGOING_REQUEST_ID_HEADER] = request_id

            return response
