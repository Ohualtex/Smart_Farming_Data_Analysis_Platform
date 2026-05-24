"""
API Key Verification Middleware
=================================
Simple API key-based authentication. Requests must send a valid key in
the `X-API-Key` header.

---

API anahtarı tabanlı kimlik doğrulama; X-API-Key header zorunludur.
"""

from fastapi import Security
from fastapi.security import APIKeyHeader

from app.config import settings
from app.middleware.exceptions import ForbiddenError, UnauthorizedError

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
        raise UnauthorizedError(detail="API anahtarı eksik. 'X-API-Key' header'ı gerekli.")

    if api_key != settings.API_KEY:
        raise ForbiddenError(detail="Geçersiz API anahtarı.")

    return api_key
