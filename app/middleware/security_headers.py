"""
Security Headers Middleware
============================
Production response header guarantee for the FastAPI app:

  Content-Security-Policy          XSS / data exfiltration defense
  Strict-Transport-Security        Force HTTPS (production only)
  X-Frame-Options: DENY            Clickjacking defense
  X-Content-Type-Options: nosniff  MIME sniffing defense
  Referrer-Policy                  PII leak via Referer header
  Permissions-Policy               Block unused browser APIs

Notes:

- CSP allowlist'i şu an dashboard'un tükettiği CDN'leri kapsar:
    * Chart.js  (jsdelivr)
    * Leaflet   (unpkg + OSM tile sunucuları)
    * Google Fonts (fonts.googleapis.com / fonts.gstatic.com)
  `'unsafe-inline'` script-src / style-src için geçici olarak açık —
  `frontend/index.html`'de 23 inline `onclick` handler ve Swagger UI'in
  inline init script'i var. B-batch refactor'unda (`main.js` ES module
  split) inline handler'lar kalkınca CSP `'unsafe-inline'` script-src
  dışına çekilebilir.

- HSTS sadece `ENVIRONMENT=production` iken eklenir; dev/HTTPS olmayan
  setup'larda eklenmesi browser'da preload yanlış pin'leyebilir.

- `/metrics` endpoint'i `include_in_schema=False` ve robotlardan uzak
  durmalı; X-Robots-Tag: noindex bunu sağlar.

---

EN/TR: Production-ready response header katmanı. CSP geçici olarak
unsafe-inline'a izin verir (B-batch sonrası daraltılabilir).
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

# Sabit header değerleri — modül seviyesi, request başına yeniden hesaplanmasın.

# CSP: virgülle değil, ;'le ayrılmış direktif listesi.
# - default-src 'self'     : tüm kategoriler için fallback
# - script-src              : kendi domain + 'unsafe-inline' (Swagger UI +
#                             inline onclick handler'lar) + Chart.js + Leaflet CDN
# - style-src               : kendi domain + 'unsafe-inline' (Leaflet popup +
#                             inline style attribute'leri) + Google Fonts CSS
# - img-src                 : kendi domain + data: (chart canvas + favicon) +
#                             OSM tile sunucuları (a/b/c.tile.openstreetmap.org)
# - font-src                : Google Fonts gstatic
# - connect-src             : kendi domain (fetch() çağrıları için)
# - frame-ancestors 'none'  : X-Frame-Options:DENY ile çakışır ama belirtmek best practice
_CSP_DIRECTIVES = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com",
    "style-src 'self' 'unsafe-inline' https://unpkg.com https://fonts.googleapis.com",
    "img-src 'self' data: https://a.tile.openstreetmap.org https://b.tile.openstreetmap.org https://c.tile.openstreetmap.org",
    "font-src 'self' https://fonts.gstatic.com",
    "connect-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
]
CSP_HEADER = "; ".join(_CSP_DIRECTIVES)

# Permissions-Policy: kullanılmayan tarayıcı API'larını proaktif kapat.
PERMISSIONS_POLICY = (
    "geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=(), gyroscope=(), accelerometer=()"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject defense-in-depth response headers on every response."""

    async def dispatch(self, request: Request, call_next) -> Response:  # noqa: ANN001
        response: Response = await call_next(request)
        # CSP — XSS + data exfiltration.
        response.headers.setdefault("Content-Security-Policy", CSP_HEADER)
        # Clickjacking.
        response.headers.setdefault("X-Frame-Options", "DENY")
        # MIME sniffing.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        # Referrer leakage.
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        # Browser API allowlist (deny by default for unused).
        response.headers.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        # HSTS — only in production (assumes HTTPS in front).
        if settings.ENVIRONMENT == "production":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        # /metrics endpoint'i public-discoverable olmasın.
        if request.url.path == "/metrics":
            response.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
        return response
