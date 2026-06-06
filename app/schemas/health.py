"""Sistem sağlığı (deep health check) Pydantic şemaları."""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.base import UtcDateTime


# ========== HEALTH (deep health check) ==========
class HealthCheckResponse(BaseModel):
    """Detayli sistem sagligi raporu."""

    status: str  # 'healthy' | 'degraded' | 'unhealthy'
    service: str
    version: str
    components: dict  # {db: ok, scheduler: ok, ml_model: ok, ...}
    timestamp: UtcDateTime
