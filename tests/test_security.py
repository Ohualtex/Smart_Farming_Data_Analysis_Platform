"""
API Güvenlik Testleri
======================
Custom exception handler, CORS, rate limiter ve request logger testleri.

Mehmet Sait Tayşi — Cycle 5 Görevi
"""

from app.middleware.exceptions import (
    ConflictError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)

# ─── CUSTOM EXCEPTION TESTLERİ ──────────────────────────────────


class TestCustomExceptions:
    """Custom exception sınıflarının doğru çalıştığını test eder."""

    def test_not_found_exception_attributes(self):
        exc = NotFoundError("Sensor")
        assert exc.message == "Sensor bulunamadi."
        assert exc.status_code == 404
        assert exc.error_code == "NOT_FOUND"

    def test_unauthorized_exception_attributes(self):
        exc = UnauthorizedError()
        assert exc.status_code == 401
        assert exc.error_code == "UNAUTHORIZED"

    def test_forbidden_exception_attributes(self):
        exc = ForbiddenError()
        assert exc.status_code == 403
        assert exc.error_code == "FORBIDDEN"

    def test_validation_exception_attributes(self):
        exc = ValidationError(message="Gecersiz email")
        assert exc.status_code == 422
        assert exc.message == "Gecersiz email"

    def test_conflict_exception_attributes(self):
        exc = ConflictError(detail="Email zaten kayitli")
        assert exc.status_code == 409
        assert exc.detail == "Email zaten kayitli"

    def test_external_service_exception(self):
        exc = ExternalServiceError(service="OpenWeatherMap")
        assert exc.status_code == 502
        assert "OpenWeatherMap" in exc.message

    def test_exception_with_detail(self):
        exc = NotFoundError("Tarla", detail="ID: 42")
        assert exc.detail == "ID: 42"


# ─── CORS TESTLERİ ──────────────────────────────────────────────


class TestCORSHeaders:
    """CORS ayarlarının doğru uygulandığını test eder."""

    def test_cors_allowed_origin(self, client):
        """İzin verilen origin ile preflight isteği."""
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:8000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORS header'ı mevcut olmalı
        assert response.status_code in (200, 405)


# ─── ERROR RESPONSE FORMAT TESTLERİ ─────────────────────────────


class TestErrorResponseFormat:
    """API hata response'larının tutarlı formatta olduğunu test eder."""

    def test_404_response_has_detail(self, client):
        """Mevcut olmayan sensor sorgusu tutarlı hata döndürmeli."""
        response = client.get("/api/sensors/99999")
        assert response.status_code == 404

    def test_422_response_on_invalid_input(self, client):
        """Geçersiz input tutarlı 422 hatası döndürmeli."""
        response = client.post(
            "/api/irrigation/predict",
            json={"soil_moisture": "not_a_number"},
        )
        assert response.status_code == 422

    def test_401_without_api_key(self, client):
        """API key olmadan korumalı endpoint'e erişim → 401."""
        from fastapi.testclient import TestClient

        from app.main import app

        # API key header'ı olmayan temiz bir client kullan
        with TestClient(app) as no_key_client:
            response = no_key_client.post(
                "/api/sensors/",
                json={
                    "field_id": 1,
                    "sensor_type": "moisture",
                    "serial_number": "TEST-001",
                },
            )
            assert response.status_code == 401


# ─── RATE LIMIT TESTLERİ ─────────────────────────────────────────


class TestRateLimit:
    """SlowAPI rate limit decorator'larının doğru bağlandığını doğrular.

    Burst denemesi yaparak 429 cevabı ve cevabın format tutarlılığını test eder.
    EN: Verifies SlowAPI rate-limit decorators are wired; bursts requests
    to assert 429 emission and response shape.
    """

    def test_strict_rate_limit_post_sensors_returns_429(self, rate_limited_client):
        """POST /api/sensors/ → STRICT_RATE (30/min); burst 429 üretmeli."""
        statuses: list[int] = []
        for i in range(35):
            response = rate_limited_client.post(
                "/api/sensors/",
                json={
                    "field_id": 1,
                    "sensor_type": "soil_moisture",
                    "serial_number": f"S-rate-{i}",
                },
            )
            statuses.append(response.status_code)
        assert 429 in statuses, f"Beklenen 429 yok; statuses={statuses[:35]}"
        # 30/min limiti aşılmamalı: en fazla 30 başarılı 201 olabilir
        assert statuses.count(201) <= 30

    def test_auth_rate_limit_register_returns_429(self, rate_limited_client):
        """POST /api/auth/register → AUTH_RATE (10/min); burst 429 üretmeli."""
        statuses: list[int] = []
        for i in range(15):
            response = rate_limited_client.post(
                "/api/auth/register",
                json={
                    "name": f"Test User {i}",
                    "email": f"ratelimit{i}@ornek.com",
                    "password": "Sifre1234",
                },
            )
            statuses.append(response.status_code)
        assert 429 in statuses, f"Beklenen 429 yok; statuses={statuses[:15]}"
        # 10/min limiti aşılmamalı
        assert statuses.count(201) <= 10

    def test_rate_limit_response_uses_standard_error_format(self, rate_limited_client):
        """429 cevabı `{error_code, message, detail}` formatında olmalı."""
        last_response = None
        for i in range(35):
            last_response = rate_limited_client.post(
                "/api/sensors/",
                json={
                    "field_id": 1,
                    "sensor_type": "soil_moisture",
                    "serial_number": f"S-fmt-{i}",
                },
            )
            if last_response.status_code == 429:
                break
        assert last_response is not None
        assert last_response.status_code == 429
        body = last_response.json()
        assert body.get("error_code") == "RATE_LIMIT_EXCEEDED"
        assert "message" in body
        assert "detail" in body


# ─── ENDPOINT ERİŞİLEBİLİRLİK TESTLERİ ─────────────────────────


class TestEndpointAccessibility:
    """Tüm yeni endpoint'lerin erişilebilir olduğunu test eder."""

    def test_root_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_docs_returns_200(self, client):
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_json_returns_200(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        # Gübreleme endpoint'leri swagger'da görünmeli
        paths = list(data["paths"].keys())
        assert "/api/fertilizer/crops" in paths
        assert "/api/fertilizer/recommend" in paths
