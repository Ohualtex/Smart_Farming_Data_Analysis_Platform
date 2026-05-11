"""
Sentry Integration
=====================
shiftFinal — A2 paketi. `SENTRY_DSN` env varsa Sentry SDK'yı başlatır;
boşsa no-op. Production'da uncaught exception'lar otomatik raporlanır.

Çağrı noktası: `app/main.py` lifespan startup.

EN: Initialise Sentry only when SENTRY_DSN is set; otherwise a no-op.
Wired in main.py lifespan startup; FastAPI integration auto-captures
uncaught exceptions.
"""

from __future__ import annotations

import sentry_sdk
from loguru import logger
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.config import settings


def init_sentry() -> bool:
    """Sentry SDK'yı başlatır. DSN boşsa no-op (False döner).

    Returns:
        True — Sentry aktive edildi
        False — DSN yok, no-op (dev/test default)
    """
    if not settings.SENTRY_DSN:
        logger.info("Sentry: SENTRY_DSN bos, devre disi (dev/test default).")
        return False

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT or settings.ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        # Default integrations: FastAPI + Starlette (request context),
        # SQLAlchemy (DB query breadcrumbs), Logging (ERROR+ events).
        integrations=[
            FastApiIntegration(),
            StarletteIntegration(),
            SqlalchemyIntegration(),
            LoggingIntegration(level=None, event_level=None),  # loguru handler manuel ekleniyor
        ],
        # PII (personally identifiable info) varsayılan kapalı; production'da
        # gerekirse `send_default_pii=True` ile açılabilir.
        send_default_pii=False,
    )

    logger.info(
        f"Sentry: aktive edildi (env={settings.SENTRY_ENVIRONMENT or settings.ENVIRONMENT}, "
        f"traces_sample_rate={settings.SENTRY_TRACES_SAMPLE_RATE})"
    )
    return True
