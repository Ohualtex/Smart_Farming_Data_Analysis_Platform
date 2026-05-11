"""
SFDAP Konfigürasyon Yönetimi
=============================
Pydantic-settings tabanlı 12-factor config. Tüm değerler `.env` dosyasından
veya environment variable'lardan okunabilir; defaults sadece **local development**
içindir.

Production'da MUTLAKA override edilmesi gereken keyler:
    - API_KEY        : İstemci kimlik doğrulaması (X-API-Key header)
    - SECRET_KEY     : İmzalama anahtarı (oturum/JWT için ileride)
    - DATABASE_URL   : Prod için PostgreSQL connection string

`ENVIRONMENT=production` set edildiğinde `_validate_production()` default secret
kullanımını engeller (fail-fast).
"""

from __future__ import annotations

import warnings

from pydantic import ConfigDict, model_validator
from pydantic_settings import BaseSettings

# Local-only sentinel'ler. Production'da bunlar görüldüğünde uygulama başlatılmaz.
_DEV_API_KEY = "dev-api-key"  # noqa: S105 — sentinel, gerçek secret değil
_DEV_SECRET_KEY = "dev-secret-key"  # noqa: S105 — sentinel, gerçek secret değil


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ─── Ortam ─────────────────────────────────────────────────
    ENVIRONMENT: str = "development"  # development | staging | production

    # ─── Veritabanı ────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./sfdap_dev.db"

    # ─── HTTP sunucu ───────────────────────────────────────────
    # Default: localhost. Container/prod için env üzerinden 0.0.0.0 verilebilir.
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    API_DEBUG: bool = True
    API_TITLE: str = "SFDAP - Akilli Tarim Veri Analizi Platformu API"
    API_VERSION: str = "1.0.0"

    # ─── Kimlik doğrulama ──────────────────────────────────────
    # Default'lar SADECE development içindir. Prod'da .env üzerinden zorunlu.
    API_KEY: str = _DEV_API_KEY
    SECRET_KEY: str = _DEV_SECRET_KEY

    # JWT (Cycle 8) — kullanıcı bazlı bearer token üretimi
    # JWT user-based bearer token settings.
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    # ─── Observability (shiftFinal — A2) ───────────────────────
    # Sentry: hata raporlama. Boş string ise devre dışı (dev/test default).
    # Production'da gerçek DSN ile aktif edilir.
    # EN: Sentry DSN; empty value disables Sentry entirely (dev/test default).
    SENTRY_DSN: str = ""
    # Sentry environment etiketi (boş ise ENVIRONMENT ile eşitlenir)
    SENTRY_ENVIRONMENT: str = ""
    # Performance transactions sample oranı (0.0 = kapalı, 1.0 = hepsi)
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    # Log formatı: "text" (renkli console default) | "json" (structured,
    # production observability stack için).
    LOG_FORMAT: str = "text"

    # ─── Dış servisler ─────────────────────────────────────────
    OPENWEATHERMAP_API_KEY: str | None = None

    # ─── ML & dosya yolları ────────────────────────────────────
    MODEL_PATH: str = "app/ml/models/"

    # ─── MQTT (Cycle 7 — IoT stream) ──────────────────────────
    # MQTT_ENABLED=false iken listener no-op kalır (test ve dev için).
    MQTT_ENABLED: bool = False
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_CLIENT_ID: str = "sfdap-listener"

    # ─── CORS ──────────────────────────────────────────────────
    # Virgülle ayrılmış origin listesi.
    CORS_ORIGINS: str = "http://localhost:8000,http://localhost:3000,http://127.0.0.1:8000"

    @model_validator(mode="after")
    def _validate_production(self) -> Settings:
        """Prod'da default secret kullanımını yasakla (fail-fast)."""
        if self.ENVIRONMENT == "production":
            insecure = []
            if self.API_KEY == _DEV_API_KEY:
                insecure.append("API_KEY")
            if self.SECRET_KEY == _DEV_SECRET_KEY:
                insecure.append("SECRET_KEY")
            if insecure:
                raise RuntimeError(
                    f"ENVIRONMENT=production iken default {', '.join(insecure)} kullanilamaz. "
                    f".env dosyasinda override edin."
                )
            if self.API_HOST == "127.0.0.1":
                warnings.warn(
                    "ENVIRONMENT=production ama API_HOST=127.0.0.1; container icinde 0.0.0.0 olmali.",
                    stacklevel=2,
                )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS_ORIGINS env string'ini liste olarak döndür."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
