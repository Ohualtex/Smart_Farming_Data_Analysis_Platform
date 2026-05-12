"""
Configuration Tests
=====================
Covers `app/config.py` — the production fail-fast validator that
refuses default secrets in production, plus CORS origin-list parsing.

---

Production'da default secret kullanımını engelleyen fail-fast validator
ve CORS origin parsing testleri.
"""

from __future__ import annotations

import warnings

import pytest

from app.config import _DEV_API_KEY, _DEV_SECRET_KEY, Settings


class TestProductionValidator:
    """`_validate_production` — ENVIRONMENT=production iken default
    secret kullanımını engellemeli (fail-fast)."""

    def test_dev_environment_allows_default_secrets(self):
        """Development modunda default secret OK, hata yok."""
        settings = Settings(
            ENVIRONMENT="development",
            API_KEY=_DEV_API_KEY,
            SECRET_KEY=_DEV_SECRET_KEY,
        )
        assert settings.API_KEY == _DEV_API_KEY

    def test_staging_environment_allows_default_secrets(self):
        """Staging modu da fail-fast tetiklemez (sadece production)."""
        settings = Settings(
            ENVIRONMENT="staging",
            API_KEY=_DEV_API_KEY,
            SECRET_KEY=_DEV_SECRET_KEY,
        )
        assert settings.ENVIRONMENT == "staging"

    def test_production_with_default_api_key_fails(self):
        """ENVIRONMENT=production + default API_KEY → RuntimeError."""
        with pytest.raises(RuntimeError, match="API_KEY"):
            Settings(
                ENVIRONMENT="production",
                API_KEY=_DEV_API_KEY,  # default — yasak
                SECRET_KEY="real-prod-secret-key-here",
            )

    def test_production_with_default_secret_key_fails(self):
        """ENVIRONMENT=production + default SECRET_KEY → RuntimeError."""
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            Settings(
                ENVIRONMENT="production",
                API_KEY="real-prod-api-key-here",
                SECRET_KEY=_DEV_SECRET_KEY,  # default — yasak
            )

    def test_production_with_both_defaults_fails_with_both_names(self):
        """İkisi de default ise mesajda her ikisi de listelenmeli."""
        with pytest.raises(RuntimeError) as exc_info:
            Settings(
                ENVIRONMENT="production",
                API_KEY=_DEV_API_KEY,
                SECRET_KEY=_DEV_SECRET_KEY,
            )
        message = str(exc_info.value)
        assert "API_KEY" in message
        assert "SECRET_KEY" in message

    def test_production_with_real_secrets_succeeds(self):
        """Tüm secret'lar gerçek değerlerle override edildiğinde OK."""
        settings = Settings(
            ENVIRONMENT="production",
            API_KEY="real-prod-api-key-secret-32-chars-xx",
            SECRET_KEY="real-prod-secret-key-secret-32-chars",
            API_HOST="0.0.0.0",  # noqa: S104 — container/prod uyumlu
        )
        assert settings.ENVIRONMENT == "production"

    def test_production_with_localhost_host_warns(self):
        """API_HOST=127.0.0.1 ile production: warning üretilmeli (container hatası)."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Settings(
                ENVIRONMENT="production",
                API_KEY="real-prod-api-key-secret-32-chars-xx",
                SECRET_KEY="real-prod-secret-key-secret-32-chars",
                API_HOST="127.0.0.1",  # warning tetiklemeli
            )
            # 'production' ve '127.0.0.1' iletisinde geçmeli
            messages = [str(warning.message) for warning in w]
            assert any("127.0.0.1" in m or "production" in m for m in messages)


class TestCorsOriginsList:
    """`cors_origins_list` property — virgülle ayrılmış string'i parse eder."""

    def test_basic_list_parsing(self):
        settings = Settings(CORS_ORIGINS="http://a.com,http://b.com")
        assert settings.cors_origins_list == ["http://a.com", "http://b.com"]

    def test_whitespace_trimmed(self):
        """Virgül etrafında boşluk olduğunda otomatik trim'lenmeli."""
        settings = Settings(CORS_ORIGINS="http://a.com  ,  http://b.com")
        assert settings.cors_origins_list == ["http://a.com", "http://b.com"]

    def test_empty_entries_filtered(self):
        """`,,a,,b,,` gibi boşlar atılmalı."""
        settings = Settings(CORS_ORIGINS=",,http://a.com,,,http://b.com,,")
        assert settings.cors_origins_list == ["http://a.com", "http://b.com"]

    def test_single_origin(self):
        settings = Settings(CORS_ORIGINS="https://farm.ornek.com")
        assert settings.cors_origins_list == ["https://farm.ornek.com"]

    def test_empty_string_yields_empty_list(self):
        settings = Settings(CORS_ORIGINS="")
        assert settings.cors_origins_list == []
