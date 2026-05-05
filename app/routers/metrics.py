"""
Sistem Metrikleri ve Derin Sağlık Kontrolü
============================================
Mevcut /api/health basit `{status: healthy}` dönerken /api/health/deep
DB bağlantısı, scheduler durumu, ML model varlığı ve disk/dosya
sistemini kontrol eder. Production'da Kubernetes liveness/readiness
probe'ları için kullanılabilir.

Mehmet Sait Tayşi — Cycle 6 Görevi (shiftSession): Model Performansını
İzleme ve Raporlama Altyapısı (deep health varyantı)

Bu modül skeleton — Mehmet tarafından metric endpoint'leri (Prometheus
exposition format gibi) eklenebilir.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.models import Sensor, SoilMoistureReading, SystemAlert
from app.schemas.schemas import HealthCheckResponse

router = APIRouter(prefix="/api/health", tags=["Sistem Metrikleri"])


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
        except Exception:  # noqa: BLE001
            pass
        return {"status": "ok", "latency_ms": latency_ms, **engine_info}
    except SQLAlchemyError as e:
        return {"status": "fail", "error": str(e)[:200]}


def _check_scheduler() -> dict:
    """APScheduler running durumu + iş listesi."""
    try:
        from app.tasks.scheduler import scheduler

        if not scheduler.running:
            return {"status": "stopped", "running": False, "jobs": []}

        jobs = []
        for job in scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                }
            )
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
)
def deep_health_check(db: Session = Depends(get_db)) -> HealthCheckResponse:
    components = {
        "db": _check_db(db),
        "scheduler": _check_scheduler(),
        "ml_model": _check_ml_model(),
        "data_freshness": _check_data_freshness(db),
        "alerts": _check_alerts(db),
        "mqtt": _check_mqtt(),
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
