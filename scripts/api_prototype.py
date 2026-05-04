"""
================================================================================
PROJE ADI: Akıllı Tarım Veri Analizi Platformu (S.F.D.A.P.)
GELİŞTİRİCİ: Mehmet Sait Taysi
BÖLÜM: Fırat Üniversitesi - Yazılım Mühendisliği
DERS: Yazılım Mühendisliğine Giriş / Proje Yönetimi
DÖNEM: 2026 Bahar Dönemi
HAFTA: 4. Hafta Görevi
GÖREV TANIMI: Temel Veri Erişim API'si (RESTful) Geliştirme,
              Güvenlik Katmanı ve Dokümantasyon Oluşturma.
--------------------------------------------------------------------------------
AÇIKLAMA:
Bu modül, platformun mikroservis mimarisindeki temel veri sağlayıcısıdır.
Toprak sensörlerinden ve meteorolojik istasyonlardan gelen verileri
standardize edilmiş JSON formatında sunar.
================================================================================
"""

from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field

# --- GÜVENLİK YAPILANDIRMASI ---
# API'yi korumak için statik bir anahtar kullanıyoruz
API_KEY = "akilli_tarim_gizli_anahtar_2026"
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Hata: Geçersiz veya eksik API Anahtarı! Verilere erişim izniniz yok.",
    )


# --- UYGULAMA TANIMLAMASI ---
app = FastAPI(
    title="Smart Farming Data Access Gateway",
    description="Fırat Üniversitesi Yazılım Mühendisliği - Akıllı Tarım Projesi Veri Erişim API'si",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# --- VERİ MODELLERİ (SCHEMA) ---
class SoilSensorData(BaseModel):
    sensor_id: str = Field(..., example="FIRAT-001")
    moisture: float = Field(..., description="Toprak nem yüzdesi")
    ph: float = Field(..., description="Toprak pH seviyesi (0-14)")
    nitrogen: int = Field(..., description="Azot miktarı (ppm)")


class WeatherData(BaseModel):
    city: str = Field(..., example="Elazığ")
    temp: float = Field(..., example=22.4)
    humidity: int = Field(..., example=40)
    summary: str = Field(..., example="Açık ve Güneşli")


# --- API UÇ NOKTALARI (ENDPOINTS) ---


@app.get("/", tags=["Genel"])
async def root():
    return {"status": "Active", "message": "Akıllı Tarım API Ağ Geçidine Hoş Geldiniz."}


@app.get("/api/v1/soil-data", response_model=list[SoilSensorData], tags=["Tarım Verileri"])
async def get_soil_measurements(api_key: str = Depends(get_api_key)):
    """Tarladaki sensörlerden gelen anlık toprak analiz verilerini döndürür."""
    # Simüle edilmiş (Mock) veriler
    return [
        {"sensor_id": "SENS-NORTH", "moisture": 44.5, "ph": 6.3, "nitrogen": 38},
        {"sensor_id": "SENS-SOUTH", "moisture": 39.2, "ph": 6.7, "nitrogen": 42},
    ]


@app.get("/api/v1/weather-data", response_model=list[WeatherData], tags=["Hava Durumu"])
async def get_local_weather(api_key: str = Depends(get_api_key)):
    """Tarımsal alanlar için meteorolojik tahmin ve anlık durum verilerini sağlar."""
    return [
        {"city": "Elazığ Merkez", "temp": 24.1, "humidity": 35, "summary": "Az Bulutlu"},
        {"city": "Baskil Bahçeleri", "temp": 21.8, "humidity": 38, "summary": "Güneşli"},
    ]
