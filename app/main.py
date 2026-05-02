"""
SFDAP API — FastAPI Giriş Noktası
====================================
Uygulamanın ana giriş noktası: FastAPI app objesini oluşturur, middleware'leri
(rate limit, CORS, request logger, exception handler) bağlar ve tüm router'ları
register eder. Lifespan'de scheduler başlatılıp kapatılır.

Tüm konfigürasyon `app.config.settings` (pydantic-settings) üzerinden gelir.
Static dashboard SPA `frontend/index.html` dosyası `/dashboard` altında
mount edilir.

Miraç Duran — Cycle 4/5/6 Görevi
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.core.logger import setup_logging
from app.database import init_db
from app.middleware.exceptions import register_exception_handlers
from app.middleware.rate_limiter import limiter, rate_limit_exceeded_handler
from app.middleware.request_logger import RequestLoggerMiddleware
from app.routers import (
    alerts,
    analytics,
    fertilizer,
    health,
    irrigation,
    metrics,
    model_performance,
    plants,
    sensors,
    weather,
)
from app.tasks.scheduler import shutdown_scheduler, start_scheduler


# Lifespan event handler (on_event yerine modern yaklaşım)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    init_db()
    start_scheduler()
    logger.info("SFDAP API baslatildi!")
    logger.info(f"Dokumantasyon: http://localhost:{settings.API_PORT}/docs")
    yield
    # Shutdown
    shutdown_scheduler()
    logger.info("SFDAP API kapatiliyor...")


# FastAPI uygulamasi
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=(
        "Akilli Tarim Veri Analizi Platformu API - "
        "Toprak sensorleri, hava durumu verileri ve bitki sagligi "
        "goruntulerini analiz ederek ciftcilere sulama optimizasyonu, "
        "gubreleme onerileri ve hastalik tahmini sunar."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── MIDDLEWARE KONFİGÜRASYONU ──────────────────────────────────

# Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Request Logger
app.add_middleware(RequestLoggerMiddleware)

# CORS ayarlari (env-driven: settings.CORS_ORIGINS virgulle ayrilmis liste)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── GLOBAL EXCEPTION HANDLER ───────────────────────────────────

register_exception_handlers(app)

# ─── ROUTER'LARI KAYDET ─────────────────────────────────────────

app.include_router(health.router)
app.include_router(sensors.router)
app.include_router(weather.router)
app.include_router(irrigation.router)
app.include_router(plants.router)
app.include_router(fertilizer.router)
app.include_router(analytics.router)

# Cycle 6 / shiftSession ekipleri tarafindan genisletilecek skeleton router'lar
app.include_router(alerts.router)  # Ecenur — Sistem Uyarilari (SystemAlert CRUD)
app.include_router(metrics.router)  # Mehmet — /api/health/deep
app.include_router(model_performance.router)  # Mehmet — Model Performans Raporlama


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "SFDAP - Akilli Tarim Veri Analizi Platformu API",
        "docs": "/docs",
        "dashboard": "/dashboard",
        "version": settings.API_VERSION,
    }


_dashboard_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(_dashboard_dir):
    app.mount("/dashboard", StaticFiles(directory=_dashboard_dir, html=True), name="dashboard")
