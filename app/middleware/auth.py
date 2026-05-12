"""
API Key Verification Middleware
=================================
Simple API key-based authentication. Requests must send a valid key in
the `X-API-Key` header.

---

API anahtarı tabanlı kimlik doğrulama; X-API-Key header zorunludur.
"""

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

# Header'dan API Key okuma
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    API Key doğrulama dependency'si.
    Geçerli bir X-API-Key header'ı yoksa 401 döndürür.

    Kullanım:
        @router.get("/endpoint", dependencies=[Depends(verify_api_key)])
        def protected_endpoint():
            ...
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API anahtari eksik. 'X-API-Key' header'i gerekli.",
        )

    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Gecersiz API anahtari.",
        )

    return api_key
