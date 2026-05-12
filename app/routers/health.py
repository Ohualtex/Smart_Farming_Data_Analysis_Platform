"""
Shallow Health Check Endpoint
===============================
`/api/health` — shallow probe for load balancers and uptime monitors.
For a deep check (DB, scheduler, model files) use `/api/health/deep`
in `app/routers/metrics.py`.

---

Sığ sağlık kontrolü uçları; derin kontrol için /api/health/deep.
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
