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
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.schemas import HealthCheckResponse

router = APIRouter(prefix="/api/health", tags=["Sistem Metrikleri"])


def _check_db(db: Session) -> dict:
    """Basit `SELECT 1` ile DB bağlantı kontrolü."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except SQLAlchemyError as e:
        return {"status": "fail", "error": str(e)[:200]}


def _check_scheduler() -> dict:
    """APScheduler running durumu."""
    try:
        from app.tasks.scheduler import scheduler

        return {
            "status": "ok" if scheduler.running else "stopped",
            "running": scheduler.running,
            "jobs": len(scheduler.get_jobs()) if scheduler.running else 0,
        }
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
    }
    overall = "healthy" if all(c.get("status") == "ok" for c in components.values()) else "degraded"
    return HealthCheckResponse(
        status=overall,
        service="SFDAP API",
        version=settings.API_VERSION,
        components=components,
        timestamp=datetime.now(UTC),
    )
