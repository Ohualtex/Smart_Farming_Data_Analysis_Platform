from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.routers import health, sensors, weather, irrigation, plants

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
)

# CORS ayarlari
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Uygulama baslarken veritabanini olustur
@app.on_event("startup")
def on_startup():
    init_db()
    print("SFDAP API baslatildi!")
    print(f"Dokumantasyon: http://localhost:{settings.API_PORT}/docs")


# Router'lari kaydet
app.include_router(health.router)
app.include_router(sensors.router)
app.include_router(weather.router)
app.include_router(irrigation.router)
app.include_router(plants.router)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "SFDAP - Akilli Tarim Veri Analizi Platformu API",
        "docs": "/docs",
        "version": settings.API_VERSION,
    }
