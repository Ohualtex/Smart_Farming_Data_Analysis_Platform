"""
SFDAP API — FastAPI Entry Point
==================================
Builds the FastAPI app, wires middleware (rate limit, CORS, request
logger, exception handler, Prometheus, request_id), registers all
routers, and runs scheduler start/stop inside the lifespan.

Configuration is driven by `app.config.settings` (pydantic-settings).
The static dashboard SPA at `frontend/index.html` is mounted under
`/dashboard`.

---

FastAPI ana giriş noktası. Middleware zincirini bağlar, router'ları
register eder, lifespan içinde scheduler'ı başlatıp kapatır. Tüm
konfigürasyon settings üzerinden, dashboard SPA `/dashboard` altında.
"""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.core.logger import setup_logging
from app.core.sentry import init_sentry
from app.database import init_db
from app.middleware.exceptions import register_exception_handlers
from app.middleware.prometheus import PrometheusMiddleware, metrics_response
from app.middleware.rate_limiter import limiter, rate_limit_exceeded_handler
from app.middleware.request_logger import RequestLoggerMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.routers import (
    alerts,
    analytics,
    auth,
    dashboard,
    farms,
    fertilizer,
    fields,
    health,
    irrigation,
    metrics,
    model_performance,
    plants,
    sensors,
    weather,
)
from app.services.mqtt_listener import mqtt_listener
from app.tasks.scheduler import shutdown_scheduler, start_scheduler


# Lifespan event handler (on_event yerine modern yaklaşım)
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup
    setup_logging()
    # Sentry — active when SENTRY_DSN env is set, otherwise no-op.
    init_sentry()
    init_db()
    start_scheduler()
    if settings.MQTT_ENABLED:
        mqtt_listener.start()
    logger.info("SFDAP API baslatildi!")
    logger.info(f"Dokumantasyon: http://localhost:{settings.API_PORT}/docs")
    yield
    # Shutdown
    shutdown_scheduler()
    if settings.MQTT_ENABLED:
        mqtt_listener.stop()
    logger.info("SFDAP API kapatiliyor...")


# Swagger UI tag'leri — her bölüm için Türkçe rehber
TAGS_METADATA = [
    {
        "name": "Sensör Verileri",
        "description": "📡 **Toprak sensörleri** ile ilgili tüm işlemler. Sensör eklemek/silmek için "
        "sağ üstteki 🔒 **Authorize** butonu üzerinden API anahtarı girin (`dev-api-key`).",
    },
    {
        "name": "Hava Durumu",
        "description": "🌤️ Çiftliklerin **hava verileri**. Sıcaklık, yağış, nem ve rüzgar bilgisi. "
        "OpenWeatherMap'ten otomatik çekilir; veriyi temizlemek için `/clean` kullanın.",
    },
    {
        "name": "Sulama Optimizasyonu",
        "description": "💧 **ML tabanlı sulama tahmini** ve sulama programı. Toprak nemini ve hava "
        "verilerini girin, model size kaç litre su gerektiğini söyler.",
    },
    {
        "name": "Gübreleme",
        "description": "🌱 **NPK önerisi** ve gübreleme takvimi. 17 bitki türü (buğday, domates, "
        "üzüm, fındık, çay, vb.) için toprak analizinize göre özelleştirilmiş öneri.",
    },
    {
        "name": "Bitki Sağlığı",
        "description": "🦠 Bitki yaprak görüntülerinin yüklenmesi ve CNN tabanlı hastalık tespiti.",
    },
    {
        "name": "Analitik & Görselleştirme",
        "description": "📊 **Toplu istatistik, dönem karşılaştırma ve PDF/Excel rapor üretimi.** "
        "Sistemdeki çiftliklerin bölge bazlı kırılımları (admin/gözetmen sistem özeti).",
    },
    {
        "name": "Çiftliğim",
        "description": "🏠 **Rol-aware tek-ekran özet** — çiftçi için kendi farm zinciri, "
        "admin/overseer/developer için sistem-geneli toplam. 4 metrik: toprak nemi, "
        "son sulama, açık uyarı, son hastalık tanısı.",
    },
    {
        "name": "Tarla Detayı",
        "description": "🌱 **Tek tarlanın tüm bağlamı** — sensörler (son okumalarıyla), sulama "
        "geçmişi, hastalık tanı geçmişi, toprak analizleri ve açık uyarılar. Yaprak foto "
        "upload → tanı demo akışının merkezi. Farmer yalnız kendi tarlasını görür.",
    },
    {
        "name": "Kullanıcı Yönetimi",
        "description": "👥 **Admin-only kullanıcı yönetimi** — tüm kullanıcıları listele, rol "
        "değiştir, yeni kullanıcı oluştur (rol seçerek), şifre sıfırla, sil. Yalnız `admin` "
        "rolü erişir; diğer roller 403 alır.",
    },
    {
        "name": "Sistem Uyarıları",
        "description": "🚨 **SystemAlert kayıtları** — sensör anomalisi, hava uyarısı, sistem "
        "hatalarının tutulduğu yer. Severity (low/medium/critical) ile filtrelenebilir.",
    },
    {
        "name": "Sistem Metrikleri",
        "description": "🩺 **Derin sağlık kontrolü** — DB, scheduler ve ML modelinin durumunu "
        "raporlar. Production'da Kubernetes liveness/readiness probe'ları için uygun.",
    },
    {
        "name": "Model Performansı",
        "description": "🤖 **ML modellerin tahmin başarı oranları** ve agregat raporlama. "
        "Hangi modelin ne kadar doğru olduğunu zaman içinde takip eder.",
    },
    {
        "name": "Health Check",
        "description": "✅ **Sığ sağlık kontrolü** — load balancer/uptime monitoring için.",
    },
    {
        "name": "Root",
        "description": "🏠 API ana sayfa.",
    },
]

# FastAPI uygulamasi
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="""
## 🌾 Akıllı Tarım Veri Analizi Platformu

Bu API, **çiftçilerin tarımsal verimliliğini artırmak** için çiftçinin kendi tarlalarından
toplanan toprak sensörleri, hava durumu verileri ve makine öğrenimi tahminlerini birleştirir.
Çiftçi yalnız kendi çiftliğini görür; admin/gözetmen tüm çiftliklerde sistem-geneli özet alır.

### 🎯 Ne sunuyoruz?

| Özellik | Açıklama |
|:--------|:---------|
| 💧 **Sulama Optimizasyonu** | Toprak nemine ve hava verilerine bakıp size kaç litre su gerektiğini söyleriz |
| 🌱 **Akıllı Gübreleme** | 17 farklı bitki türü için NPK (azot/fosfor/potasyum) önerisi |
| 📊 **Analitik** | 7 coğrafi bölge bazlı karşılaştırma, PDF/Excel rapor |
| 🚨 **İzleme** | Sensör anomalisi, hava uyarısı, sistem hataları |

### 🔐 API Anahtarı

Yazma işlemleri (POST/DELETE/PATCH) `X-API-Key` header'ı ister.
Yukarıdaki **🔒 Authorize** butonuna tıklayıp şu anahtarı girin: `dev-api-key`

### 🏃 Hızlı Test

1. Aşağıda bir endpoint seç (örn. `/api/fertilizer/recommend`)
2. **Try it out** → istenen alanları doldur (örnek değerler önceden gelir)
3. **Execute** → cevabı aşağıda gör

### 📚 Daha kapsamlı kullanım kılavuzu

`docs/api/API_Kullanim_Kilavuzu.md` dosyası — curl örnekleri, hata kodları, Postman import.

### 👥 Bu Platform Hakkında

**SFDAP**, 5 kişilik öğrenci ekibi tarafından geliştirilen Scrum tabanlı bir projedir.
Çiftçi-odaklı bir saha aracıdır; admin/gözetmen rolleri sistem-geneli gözetim sağlar.
""",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
)

# ─── MIDDLEWARE KONFİGÜRASYONU ──────────────────────────────────

# Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Prometheus instrumentation — request counter + duration histogram.
# Added before RequestLoggerMiddleware so every response (including
# failures) is counted.
# ---
# Prometheus instrumentation; request logger'dan önce eklenir ki hata
# dahil tüm response'lar metrik'e yansısın.
app.add_middleware(PrometheusMiddleware)

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

# Defense-in-depth response header'ları (CSP, HSTS, XFO, XCTO, Referrer-Policy,
# Permissions-Policy). En son eklendi → tüm middleware/router yanıtlarına
# yansır. CORS'tan sonra eklenmeli ki preflight OPTIONS'lara da yansısın.
app.add_middleware(SecurityHeadersMiddleware)

# ─── GLOBAL EXCEPTION HANDLER ───────────────────────────────────

register_exception_handlers(app)

# ─── ROUTER'LARI KAYDET ─────────────────────────────────────────

app.include_router(health.router)
app.include_router(farms.router)
app.include_router(fields.router)
app.include_router(sensors.router)
app.include_router(weather.router)
app.include_router(irrigation.router)
app.include_router(plants.router)
app.include_router(fertilizer.router)
app.include_router(analytics.router)
app.include_router(dashboard.router)

app.include_router(alerts.router)
app.include_router(metrics.router)
app.include_router(model_performance.router)
app.include_router(auth.router)


@app.get("/", tags=["Root"])
def root() -> dict:
    return {
        "message": "SFDAP - Akilli Tarim Veri Analizi Platformu API",
        "docs": "/docs",
        "dashboard": "/dashboard",
        "version": settings.API_VERSION,
    }


# Prometheus metrics endpoint — text/plain exposition format.
# Path Prometheus konvansiyonuna uygun olarak prefix'siz `/metrics`.
# Scrape config örneği: scrape_interval 30s, target 'sfdap_api:8000'.
# EN: Prometheus scrape endpoint; standard `/metrics` path (no prefix).
@app.get("/metrics", include_in_schema=False)
def prometheus_metrics() -> Response:
    return metrics_response()


_dashboard_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(_dashboard_dir):
    app.mount("/dashboard", StaticFiles(directory=_dashboard_dir, html=True), name="dashboard")

# Bitki sağlığı görsel upload'ları (plants.py içinde URL üretiliyor)
_plant_uploads_dir = os.path.join(os.path.dirname(__file__), "ml", "plant_uploads")
if os.path.isdir(_plant_uploads_dir):
    app.mount(
        "/static/plant_uploads",
        StaticFiles(directory=_plant_uploads_dir),
        name="plant_uploads",
    )
