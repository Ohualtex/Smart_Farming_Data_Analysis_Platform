from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["Health Check"])


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "SFDAP API",
        "version": "1.0.0"
    }
