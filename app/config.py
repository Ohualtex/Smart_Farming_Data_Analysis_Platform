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
    """Pydantic-settings driven application configuration (12-factor)."""

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ─── Ortam ─────────────────────────────────────────────────
    ENVIRONMENT: str = "development"  # development | staging | production

    # ─── Veritabanı ────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./sfdap_dev.db"

    # Connection pool tuning (sadece PostgreSQL/MySQL'de aktif; SQLite
    # tek-connection olduğu için bu ayarlar yok sayılır).
    # EN: Pool tuning applies only when DATABASE_URL is non-SQLite.
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_PRE_PING: bool = True  # ölü connection'ları kullanmadan önce ping
    DB_POOL_RECYCLE: int = 3600  # 1 saatte connection recycle (MySQL/PG drop koruması)

    # ─── HTTP sunucu ───────────────────────────────────────────
    # Default: localhost. Container/prod için env üzerinden 0.0.0.0 verilebilir.
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    # echo'yu sürer → prod'da tüm SQL + parametreler (şifre hash/PII) log'a sızar
    # (audit YÜKSEK). Güvenli default = False; dev'de .env ile True yapılabilir.
    API_DEBUG: bool = False
    API_TITLE: str = "SFDAP - Akilli Tarim Veri Analizi Platformu API"
    API_VERSION: str = "1.0.0"

    # ─── Kimlik doğrulama ──────────────────────────────────────
    # Default'lar SADECE development içindir. Prod'da .env üzerinden zorunlu.
    API_KEY: str = _DEV_API_KEY
    SECRET_KEY: str = _DEV_SECRET_KEY

    # JWT user-based bearer token settings.
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    # ─── Observability ─────────────────────────────────────────
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

    # Log seviyesi: DEBUG | INFO | WARNING | ERROR | CRITICAL.
    # Console handler bu seviyeden itibaren yazar; file handler ayrıca
    # WARNING'in altına inmez (üretim disk tasarrufu).
    LOG_LEVEL: str = "INFO"

    # Slow-request eşiği (ms). RequestLoggerMiddleware'de bu eşiği aşan
    # istekler WARN seviyesinde "slow" tag'iyle yansır (perf gözlemi).
    LOG_SLOW_REQUEST_MS: int = 1000

    # ─── Dış servisler ─────────────────────────────────────────
    OPENWEATHERMAP_API_KEY: str | None = None

    # ─── ML & dosya yolları ────────────────────────────────────
    MODEL_PATH: str = "app/ml/models/"

    # ─── MQTT (IoT sensor stream) ─────────────────────────────
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
        """Prod'da güvenlik açıklarını yasakla (fail-fast).

        Kontrol edilenler:
            * Default API_KEY / SECRET_KEY (dev sentinel'leri)
            * CORS_ORIGINS içinde wildcard `*` veya `localhost`/`127.0.0.1`
            * API_HOST=127.0.0.1 (container içinde 0.0.0.0 olmalı — warning)
        """
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
            # CORS allowlist hijack defense: production'da `*` veya local
            # origin'ler attack surface açar (CSRF, credential exfil).
            insecure_origins = [o for o in self.cors_origins_list if o == "*" or "localhost" in o or "127.0.0.1" in o]
            if insecure_origins:
                raise RuntimeError(
                    f"ENVIRONMENT=production iken CORS_ORIGINS guvensiz origin'ler "
                    f"icermemeli: {insecure_origins}. .env dosyasinda gercek "
                    f"domain'leri set edin (ornek: https://app.ornek.com)."
                )
            if self.API_HOST == "127.0.0.1":
                warnings.warn(
                    "ENVIRONMENT=production ama API_HOST=127.0.0.1; container icinde 0.0.0.0 olmali.",
                    stacklevel=2,
                )
            if self.API_DEBUG:
                warnings.warn(
                    "ENVIRONMENT=production ama API_DEBUG=True; SQLAlchemy echo SQL+parametreleri "
                    "(sifre hash/PII) log'a yazar. .env'de API_DEBUG=False yapin "
                    "(echo yine de prod'da zorla kapatilir, bkz. database.py).",
                    stacklevel=2,
                )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS_ORIGINS env string'ini liste olarak döndür."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
