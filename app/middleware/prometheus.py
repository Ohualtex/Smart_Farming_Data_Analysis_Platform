"""
Prometheus Metrics Middleware
==================================
shiftFinal — A2 paketi. HTTP request'leri Prometheus counter ve histogram
metriklerine kayıt eden middleware + `/metrics` endpoint helper'ı.

Yayılan metrikler:
- `sfdap_http_requests_total{method, path, status}` — Counter
- `sfdap_http_request_duration_seconds{method, path}` — Histogram
- `sfdap_model_predictions_total{model_name}` — Counter (ML inference sayacı)
- `sfdap_active_alerts{severity}` — Gauge (kritik durum izleme)

`/metrics` endpoint'i `app/routers/metrics.py` içinde wire ediliyor.

EN: Prometheus instrumentation middleware. Records request count and
duration histograms per (method, path, status). Also exposes model
prediction and active-alert counters/gauges used by other modules.
"""

from __future__ import annotations

import time

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Standalone registry — global default'ı kirletmemek için.
# Test isolation'da bu registry sıfırlanabilir.
# EN: Standalone registry keeps the global default clean; testable.
REGISTRY = CollectorRegistry(auto_describe=True)

# ─── Metric tanımları ──────────────────────────────────────────────────

HTTP_REQUESTS_TOTAL = Counter(
    "sfdap_http_requests_total",
    "Toplam HTTP istek sayısı",
    labelnames=("method", "path", "status"),
    registry=REGISTRY,
)

HTTP_REQUEST_DURATION = Histogram(
    "sfdap_http_request_duration_seconds",
    "HTTP istek süresi (saniye)",
    labelnames=("method", "path"),
    # Default Prometheus bucket'ları — milisaniyeden saniyeye API yanıtları için
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)

MODEL_PREDICTIONS_TOTAL = Counter(
    "sfdap_model_predictions_total",
    "ML model tahmin sayısı (router'lardan elle artırılır)",
    labelnames=("model_name",),
    registry=REGISTRY,
)

ACTIVE_ALERTS_GAUGE = Gauge(
    "sfdap_active_alerts",
    "Aktif (çözülmemiş) sistem alert sayısı, severity bazlı",
    labelnames=("severity",),
    registry=REGISTRY,
)


def _normalize_path(path: str) -> str:
    """Path'i metrik label'ı olarak normalize et.

    `/api/sensors/42` gibi dinamik path'ler high-cardinality yapar
    (her ID için ayrı label). Sayıları `{id}` placeholder'ına çeviriyoruz.

    EN: Replace numeric segments with `{id}` so per-id paths don't blow up
    label cardinality.
    """
    parts = path.split("/")
    normalized = ["{id}" if p.isdigit() else p for p in parts]
    return "/".join(normalized)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Her HTTP request'i Prometheus metriklerine yansıtır.

    `/metrics` endpoint'i hariç (recursive metric trafiğini önlemek için).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # /metrics endpoint'inin kendi metriklerini ölçmüyoruz (recursive olur)
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        path = _normalize_path(request.url.path)
        start = time.perf_counter()

        try:
            response = await call_next(request)
            status = str(response.status_code)
        except Exception:
            # Exception case'i — 500 olarak say
            HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status="500").inc()
            HTTP_REQUEST_DURATION.labels(method=method, path=path).observe(time.perf_counter() - start)
            raise

        HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status=status).inc()
        HTTP_REQUEST_DURATION.labels(method=method, path=path).observe(time.perf_counter() - start)
        return response


def metrics_response() -> Response:
    """`/metrics` endpoint cevabı — Prometheus text format.

    Bu fonksiyon `app/routers/metrics.py` içinde route'a bağlanır.
    EN: Helper for the /metrics route — emits the Prometheus text exposition
    format from the standalone registry.
    """
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )
