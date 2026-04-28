import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import init_db
from app.middleware.exceptions import register_exception_handlers
from app.middleware.rate_limiter import limiter, rate_limit_exceeded_handler
from app.middleware.request_logger import RequestLoggerMiddleware
from app.routers import analytics, fertilizer, health, irrigation, plants, sensors, weather


# Lifespan event handler (on_event yerine modern yaklaşım)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    print("SFDAP API baslatildi!")
    print(f"Dokumantasyon: http://localhost:{settings.API_PORT}/docs")
    yield
    # Shutdown
    print("SFDAP API kapatiliyor...")


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

# CORS ayarlari (güvenli: spesifik origin'ler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
    ],
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


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "SFDAP - Akilli Tarim Veri Analizi Platformu API",
        "docs": "/docs",
        "dashboard": "/dashboard",
        "version": settings.API_VERSION,
    }


_dashboard_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Ecenur_Uner")
if os.path.isdir(_dashboard_dir):
    app.mount("/dashboard", StaticFiles(directory=_dashboard_dir, html=True), name="dashboard")
