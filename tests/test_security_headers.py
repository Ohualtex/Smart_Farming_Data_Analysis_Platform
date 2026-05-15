"""
Security Headers + CORS Production Guard Testleri
==================================================
SecurityHeadersMiddleware'in her response'a 5 (dev) / 6 (prod) header
eklediğini, ve `Settings` validator'unun production'da güvensiz CORS
origin'leri reddettiğini doğrular.
"""

from __future__ import annotations

import pytest

from app.config import _DEV_API_KEY, _DEV_SECRET_KEY, Settings

# ───── SecurityHeadersMiddleware ─────────────────────────────────────


class TestSecurityHeaders:
    """Defense-in-depth response header'lar her endpoint'te mevcut mu?"""

    def test_csp_header_present_and_well_formed(self, client):
        r = client.get("/api/health")
        csp = r.headers.get("Content-Security-Policy")
        assert csp is not None
        # Anahtar direktifler — CDN'ler ve self izinli, frame-ancestors 'none'
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "https://cdn.jsdelivr.net" in csp  # Chart.js
        assert "https://unpkg.com" in csp  # Leaflet
        assert "https://a.tile.openstreetmap.org" in csp  # OSM tiles

    def test_x_frame_options_deny(self, client):
        r = client.get("/api/health")
        assert r.headers.get("X-Frame-Options") == "DENY"

    def test_x_content_type_options_nosniff(self, client):
        r = client.get("/api/health")
        assert r.headers.get("X-Content-Type-Options") == "nosniff"

    def test_referrer_policy_strict_origin(self, client):
        r = client.get("/api/health")
        assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy_blocks_unused_apis(self, client):
        r = client.get("/api/health")
        pp = r.headers.get("Permissions-Policy")
        assert pp is not None
        for api in ("geolocation", "microphone", "camera", "payment"):
            assert f"{api}=()" in pp

    def test_hsts_absent_in_dev(self, client):
        """Dev mode: HSTS HEADER YOK (HTTPS olmadan yanlış pin'leme riski)."""
        r = client.get("/api/health")
        assert "Strict-Transport-Security" not in r.headers

    def test_metrics_endpoint_has_no_index(self, client):
        """Prometheus /metrics: search engine + robotlardan uzak."""
        r = client.get("/metrics")
        assert r.status_code == 200
        assert r.headers.get("X-Robots-Tag") == "noindex, nofollow"

    def test_headers_persist_on_error_responses(self, client):
        """404 gibi error response'larda da güvenlik header'ları olmalı."""
        r = client.get("/api/sensors/9999999")
        assert r.status_code == 404
        # Middleware her response'a ekler — error case dahil
        assert r.headers.get("X-Frame-Options") == "DENY"
        assert r.headers.get("X-Content-Type-Options") == "nosniff"


# ───── Settings: CORS Production Guard ───────────────────────────────


class TestCorsProductionGuard:
    """`_validate_production` CORS origin denetimleri."""

    def test_production_with_wildcard_cors_fails(self):
        with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
            Settings(
                ENVIRONMENT="production",
                API_KEY="real-prod-key-32char-minimum-aaaaa",
                SECRET_KEY="real-prod-secret-32char-minimum-aaa",
                CORS_ORIGINS="*",
            )

    def test_production_with_localhost_cors_fails(self):
        with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
            Settings(
                ENVIRONMENT="production",
                API_KEY="real-prod-key-32char-minimum-aaaaa",
                SECRET_KEY="real-prod-secret-32char-minimum-aaa",
                CORS_ORIGINS="http://localhost:3000",
            )

    def test_production_with_127_loopback_cors_fails(self):
        with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
            Settings(
                ENVIRONMENT="production",
                API_KEY="real-prod-key-32char-minimum-aaaaa",
                SECRET_KEY="real-prod-secret-32char-minimum-aaa",
                CORS_ORIGINS="http://127.0.0.1:8000",
            )

    def test_production_with_real_domain_cors_succeeds(self):
        s = Settings(
            ENVIRONMENT="production",
            API_KEY="real-prod-key-32char-minimum-aaaaa",
            SECRET_KEY="real-prod-secret-32char-minimum-aaa",
            CORS_ORIGINS="https://app.sfdap.example.com,https://admin.sfdap.example.com",
        )
        assert s.cors_origins_list == [
            "https://app.sfdap.example.com",
            "https://admin.sfdap.example.com",
        ]

    def test_dev_environment_allows_localhost_cors(self):
        """Dev'de localhost serbest (validator sadece production'da çalışır)."""
        s = Settings(
            ENVIRONMENT="development",
            API_KEY=_DEV_API_KEY,
            SECRET_KEY=_DEV_SECRET_KEY,
            CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:8000",
        )
        assert "http://localhost:3000" in s.cors_origins_list
