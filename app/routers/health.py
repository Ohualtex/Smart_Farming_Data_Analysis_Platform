"""
Basit Sağlık Kontrolü Endpoint'i
=================================
`/api/health` — load balancer ve uptime monitoring için sığ kontrol.
Detaylı kontrol için `/api/health/deep` (`app/routers/metrics.py`).

Mehmet Sait Tayşi — Cycle 4 Görevi
"""

from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/api", tags=["Health Check"])


@router.get(
    "/health",
    summary="Sığ sağlık kontrolü",
    description="Servisin ayakta olduğunu hızlıca doğrulamak için minimal endpoint. "
    "Load balancer / uptime probe'ları için uygundur.",
)
def health_check():
    return {"status": "healthy", "service": "SFDAP API", "version": settings.API_VERSION}
