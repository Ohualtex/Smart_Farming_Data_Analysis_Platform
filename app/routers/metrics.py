"""
System Metrics and Deep Health Probe
======================================
While `/api/health` returns a shallow `{status: healthy}`,
`/api/health/deep` checks DB connectivity, scheduler status, ML model
presence, and disk/file-system. Suitable as a Kubernetes
liveness/readiness probe.

---

`/api/health` yüzeysel, `/api/health/deep` ise DB + scheduler + model
+ disk kontrolü yapar. K8s liveness/readiness probe için uygundur.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.models import Sensor, SoilMoistureReading, SystemAlert
from app.routers.auth import require_role
from app.schemas.schemas import HealthCheckResponse

router = APIRouter(prefix="/api/health", tags=["Sistem Metrikleri"])

# Uygulama başlangıç zamanı (modül import — uvicorn worker ilk yüklendiğinde).
# Uptime hesaplaması için kullanılır. v3-7.
_STARTED_AT = datetime.now(UTC)


def _check_uptime() -> dict:
    """Uygulama uptime (saniye) — basit gauge."""
    seconds = int((datetime.now(UTC) - _STARTED_AT).total_seconds())
    return {"status": "ok", "uptime_seconds": seconds, "started_at": _STARTED_AT.isoformat()}


def _check_db(db: Session) -> dict:
    """`SELECT 1` ile DB bağlantı + latency kontrolü."""
    try:
        t0 = time.perf_counter()
        db.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        # Connection pool durumu (varsa)
        engine_info = {}
        try:
            from app.database import engine

            pool = engine.pool
            engine_info = {
                "dialect": engine.dialect.name,
                "pool_size": getattr(pool, "size", lambda: None)() if callable(getattr(pool, "size", None)) else None,
                "checked_out": getattr(pool, "checkedout", lambda: None)()
                if callable(getattr(pool, "checkedout", None))
                else None,
            }
        except Exception as exc:  # noqa: BLE001
            # Pool detayları opsiyonel — alınamadıysa sadece debug log,
            # /health/deep yine ok döner.
            # EN: Optional pool details; if introspection fails, just debug log
            # and let /health/deep proceed with status=ok.
            from loguru import logger as _logger

            _logger.debug(f"engine_info introspection failed: {exc}")
        return {"status": "ok", "latency_ms": latency_ms, **engine_info}
    except SQLAlchemyError as e:
        return {"status": "fail", "error": str(e)[:200]}


def _check_scheduler() -> dict:
    """APScheduler running durumu + iş listesi."""
    try:
        from app.tasks.scheduler import scheduler

        if not scheduler.running:
            return {"status": "stopped", "running": False, "jobs": []}

        jobs = [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
            for job in scheduler.get_jobs()
        ]
        return {"status": "ok", "running": True, "job_count": len(jobs), "jobs": jobs}
    except Exception as e:  # noqa: BLE001
        return {"status": "fail", "error": str(e)[:200]}


def _check_ml_model() -> dict:
    """Sulama ML modeli pickle dosyası mevcut mu."""
    model_file = os.path.join(settings.MODEL_PATH, "irrigation_model.pkl")
    scaler_file = os.path.join(settings.MODEL_PATH, "scaler.pkl")
    if os.path.exists(model_file) and os.path.exists(scaler_file):
        return {
            "status": "ok",
            "model_size_bytes": os.path.getsize(model_file),
            "scaler_size_bytes": os.path.getsize(scaler_file),
        }
    return {"status": "fail", "error": "model veya scaler dosyasi yok"}


def _check_data_freshness(db: Session) -> dict:
    """Aktif sensör sayısı + son 1 saatte gelen okuma sayısı."""
    try:
        active_sensors = db.query(func.count(Sensor.id)).filter(Sensor.status == "active").scalar() or 0
        since = datetime.now(UTC) - timedelta(hours=1)
        recent_readings = (
            db.query(func.count(SoilMoistureReading.id)).filter(SoilMoistureReading.reading_timestamp >= since).scalar()
            or 0
        )
        return {
            "status": "ok",
            "active_sensors": active_sensors,
            "readings_last_hour": recent_readings,
        }
    except SQLAlchemyError as e:
        return {"status": "fail", "error": str(e)[:200]}


def _check_mqtt() -> dict:
    """MQTT listener durumu (broker connection)."""
    try:
        from app.services.mqtt_listener import mqtt_listener

        status = mqtt_listener.status()
        # MQTT_ENABLED=false ise sistem sağlıksız sayılmaz
        if not status["enabled"]:
            return {"status": "disabled", **status}
        return {"status": "ok" if status["connected"] else "degraded", **status}
    except Exception as e:  # noqa: BLE001
        return {"status": "fail", "error": str(e)[:200]}


def _check_alerts(db: Session) -> dict:
    """Aktif (unresolved) alert sayıları."""
    try:
        critical = (
            db.query(func.count(SystemAlert.id))
            .filter(SystemAlert.severity == "critical", SystemAlert.is_resolved.is_(False))
            .scalar()
            or 0
        )
        medium = (
            db.query(func.count(SystemAlert.id))
            .filter(SystemAlert.severity == "medium", SystemAlert.is_resolved.is_(False))
            .scalar()
            or 0
        )
        low = (
            db.query(func.count(SystemAlert.id))
            .filter(SystemAlert.severity == "low", SystemAlert.is_resolved.is_(False))
            .scalar()
            or 0
        )
        # Critical varsa sistem stresli kabul edilir
        status = "ok" if critical == 0 else "degraded"
        return {
            "status": status,
            "critical": critical,
            "medium": medium,
            "low": low,
        }
    except SQLAlchemyError as e:
        return {"status": "fail", "error": str(e)[:200]}


@router.get(
    "/deep",
    response_model=HealthCheckResponse,
    summary="Derin sistem sağlığı kontrolü",
    description="DB, scheduler ve ML model bileşenlerini kontrol eder. "
    "Herhangi bir bileşen 'fail' olursa overall 'degraded' döndürür.",
    # AUDIT FIX (#6): scheduler iş listesi / pool internals / ham DB hata
    # string'leri sızdıran bu uç artık yalnız admin/developer'a açık.
    dependencies=[Depends(require_role("admin", "developer"))],
    responses={401: {"description": "Bearer token gerekli"}, 403: {"description": "admin/developer rolü gerekli"}},
)
def deep_health_check(db: Session = Depends(get_db)) -> HealthCheckResponse:
    components = {
        "db": _check_db(db),
        "scheduler": _check_scheduler(),
        "ml_model": _check_ml_model(),
        "data_freshness": _check_data_freshness(db),
        "alerts": _check_alerts(db),
        "mqtt": _check_mqtt(),
        "uptime": _check_uptime(),
    }
    # Bileşen durumlarını birleştir: 'fail' → unhealthy, 'degraded'/'stopped' → degraded,
    # aksi takdirde healthy. 'disabled' (MQTT_ENABLED=false) sağlıksızlık sayılmaz.
    statuses = [c.get("status") for c in components.values()]
    if any(s == "fail" for s in statuses):
        overall = "unhealthy"
    elif any(s in ("degraded", "stopped") for s in statuses):
        overall = "degraded"
    else:
        overall = "healthy"
    return HealthCheckResponse(
        status=overall,
        service="SFDAP API",
        version=settings.API_VERSION,
        components=components,
        timestamp=datetime.now(UTC),
    )


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="Prometheus text format metrikleri (v3-7)",
    description=(
        "Prometheus scrape endpoint'i — text/plain format'ta sistem metrikleri "
        "(uptime, aktif sensör sayısı, çözülmemiş alert sayıları). Hafif, harici "
        "library bağımlılığı olmadan basit gauge'lar yayar. Production'da bir "
        "Prometheus instance'ı buradan periyodik scrape eder."
    ),
    # AUDIT FIX (#6): aktif sensör / alert sayıları gibi sistem iç metriklerini
    # sızdıran scrape ucu artık yalnız admin/developer'a açık.
    dependencies=[Depends(require_role("admin", "developer"))],
    responses={
        200: {"content": {"text/plain": {}}, "description": "Prometheus exposition format"},
        401: {"description": "Bearer token gerekli"},
        403: {"description": "admin/developer rolü gerekli"},
    },
)
def prometheus_metrics(db: Session = Depends(get_db)) -> PlainTextResponse:
    """Lightweight Prometheus exposition — manual text format (no client_python dep)."""
    # Uptime
    uptime_seconds = int((datetime.now(UTC) - _STARTED_AT).total_seconds())
    # Aktif sensör sayısı + son saat okumalar
    try:
        active_sensors = db.query(func.count(Sensor.id)).filter(Sensor.status == "active").scalar() or 0
        since = datetime.now(UTC) - timedelta(hours=1)
        readings_last_hour = (
            db.query(func.count(SoilMoistureReading.id)).filter(SoilMoistureReading.reading_timestamp >= since).scalar()
            or 0
        )
    except SQLAlchemyError:
        active_sensors = 0
        readings_last_hour = 0
    # Çözülmemiş alert sayıları (severity bazlı)
    try:
        alert_counts = dict(
            db.query(SystemAlert.severity, func.count(SystemAlert.id))
            .filter(SystemAlert.is_resolved.is_(False))
            .group_by(SystemAlert.severity)
            .all()
        )
    except SQLAlchemyError:
        alert_counts = {}

    lines = [
        "# HELP sfdap_uptime_seconds Uygulama uptime (saniye)",
        "# TYPE sfdap_uptime_seconds counter",
        f"sfdap_uptime_seconds {uptime_seconds}",
        "",
        "# HELP sfdap_active_sensors Aktif (status='active') sensör sayısı",
        "# TYPE sfdap_active_sensors gauge",
        f"sfdap_active_sensors {active_sensors}",
        "",
        "# HELP sfdap_readings_last_hour Son 1 saatte gelen toprak nemi okuma sayısı",
        "# TYPE sfdap_readings_last_hour gauge",
        f"sfdap_readings_last_hour {readings_last_hour}",
        "",
        "# HELP sfdap_alerts_unresolved Çözülmemiş sistem uyarısı sayısı (severity etiketi)",
        "# TYPE sfdap_alerts_unresolved gauge",
    ]
    lines.extend(
        f'sfdap_alerts_unresolved{{severity="{severity}"}} {alert_counts.get(severity, 0)}'
        for severity in ("critical", "medium", "low")
    )
    lines.append("")
    return PlainTextResponse("\n".join(lines), media_type="text/plain; version=0.0.4; charset=utf-8")
