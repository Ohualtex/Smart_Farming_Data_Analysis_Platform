"""
SFDAP Pydantic Şemaları
========================
Sensör, hava durumu, sulama, gübreleme, bitki sağlığı, analitik ve
sistem uyarıları için Pydantic v2 model'leri.

Kapsam dışı (henüz endpoint'lerce tüketilmediği için bu modülde tanımlı değil):
- User / Farm / Field / SoilAnalysis / CropPlanting / FertilizerRecommendationLog

Auth schema'ları `app/routers/auth.py` içinde tanımlıdır
(UserRegisterRequest, UserLoginRequest, TokenResponse, CurrentUserResponse).
CRUD endpoint'leri eklendiğinde schema'lar burada yeniden tanımlanmalı.

EN: Pydantic v2 schemas for sensor, weather, irrigation, fertilizer, plant
health, analytics and system alerts. Auth schemas live in app/routers/auth.py.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer


def _serialize_utc(value: datetime) -> str:
    """Always emit RFC 3339 `date-time` with a UTC suffix.

    SQLAlchemy returns naive datetimes from SQLite; without this
    serializer the JSON output ("2026-05-02T22:48:07.191981") fails
    OpenAPI `format: date-time` validation (no timezone offset).
    Naive values are interpreted as UTC.

    ---

    SQLAlchemy SQLite'tan tz'siz datetime döndürür; bu serializer hep
    UTC suffix'li ISO 8601 üretip OpenAPI `date-time` kontratıyla uyumlu
    JSON çıkarır.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


UtcDateTime = Annotated[
    datetime,
    PlainSerializer(_serialize_utc, return_type=str, when_used="json"),
]


# ========== SENSOR ==========
class SensorCreate(BaseModel):
    """Create payload for Sensor."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "field_id": 1,
                "sensor_type": "soil_moisture",
                "serial_number": "SN-2026-001",
                "depth_cm": 20.0,
                "lat": 41.0082,
                "lng": 28.9784,
            }
        }
    )

    field_id: int
    sensor_type: str  # 'soil_moisture' | 'soil_temperature' | 'humidity' | ...
    serial_number: str
    depth_cm: float | None = None
    lat: float | None = None
    lng: float | None = None


class SensorResponse(BaseModel):
    """Sensor serializer (response shape)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    field_id: int
    sensor_type: str
    serial_number: str
    status: str


# ========== SENSOR READING ==========
class SensorReadingCreate(BaseModel):
    """Create payload for SensorReading."""

    sensor_id: int
    moisture_percent: float
    depth_cm: float | None = None
    soil_temperature_c: float | None = None
    electrical_conductivity: float | None = None


class SensorReadingResponse(BaseModel):
    """SensorReading serializer (response shape)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    sensor_id: int
    reading_timestamp: UtcDateTime
    moisture_percent: float
    soil_temperature_c: float | None


# ========== WEATHER ==========
class WeatherDataCreate(BaseModel):
    """Create payload for WeatherData."""

    farm_id: int
    temperature_c: float | None = None
    humidity_percent: float | None = None
    precipitation_mm: float | None = None
    wind_speed_kmh: float | None = None


class WeatherDataResponse(BaseModel):
    """WeatherData serializer (response shape)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    farm_id: int | None
    recorded_at: UtcDateTime
    temperature_c: float | None
    humidity_percent: float | None
    precipitation_mm: float | None


# ========== IRRIGATION ==========
class IrrigationCreate(BaseModel):
    """Create payload for Irrigation."""

    field_id: int
    scheduled_date: datetime
    duration_min: int | None = None
    water_amount_liters: float | None = None


class IrrigationResponse(BaseModel):
    """Irrigation serializer (response shape)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    field_id: int
    scheduled_date: UtcDateTime
    water_amount_liters: float | None
    status: str


class IrrigationPredictionRequest(BaseModel):
    """IrrigationPrediction endpoint request body."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "soil_moisture": 30.0,
                "soil_temperature": 22.0,
                "humidity": 60.0,
                "temperature": 25.0,
                "precipitation": 2.0,
            }
        }
    )

    # Range constraints prevent numerical overflow in the downstream
    # RandomForest predict step (extreme floats blow up numpy ops).
    # ---
    # Aralık kısıtları RandomForest predict adımında sayısal overflow'u
    # engeller; uç değerler numpy işlemlerini patlatır.
    soil_moisture: float = Field(..., ge=0.0, le=100.0)  # %0-100 toprak nemi
    soil_temperature: float = Field(..., ge=-50.0, le=80.0)  # °C
    humidity: float = Field(..., ge=0.0, le=100.0)  # %0-100 hava nemi
    temperature: float = Field(..., ge=-60.0, le=70.0)  # °C hava sıcaklığı
    precipitation: float = Field(..., ge=0.0, le=1000.0)  # 24 saat yağış (mm)


class IrrigationPredictionResponse(BaseModel):
    """IrrigationPrediction serializer (response shape)."""

    recommended_water_liters: float
    irrigation_needed: bool
    confidence: float
    message: str


# ========== FERTILIZER (Gübreleme) ==========
class FertilizerRecommendRequest(BaseModel):
    """FertilizerRecommend endpoint request body."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "crop_type": "tomato",
                "soil_nitrogen": 80.0,
                "soil_phosphorus": 40.0,
                "soil_potassium": 50.0,
                "area_hectares": 1.0,
            }
        }
    )

    # crop_type: wheat | corn | barley | rice | tomato | pepper | potato | cotton |
    # sunflower | sugar_beet | olive | grape | apple | citrus | hazelnut | pistachio | tea
    crop_type: str
    soil_nitrogen: float  # mg/kg
    soil_phosphorus: float  # mg/kg
    soil_potassium: float  # mg/kg
    area_hectares: float


class FertilizerRecommendResponse(BaseModel):
    """FertilizerRecommend serializer (response shape)."""

    crop_type: str
    crop_name_tr: str
    area_hectares: float
    soil_analysis: dict
    deficit: dict
    nitrogen_needed_kg: float
    phosphorus_needed_kg: float
    potassium_needed_kg: float
    total_fertilizer_kg: float
    recommendation: str


class FertilizerScheduleRequest(BaseModel):
    """FertilizerSchedule endpoint request body."""

    crop_type: str
    planting_date: str  # YYYY-MM-DD
    area_hectares: float
    soil_nitrogen: float = 0.0
    soil_phosphorus: float = 0.0
    soil_potassium: float = 0.0


class FertilizerScheduleResponse(BaseModel):
    """FertilizerSchedule serializer (response shape)."""

    phase: str
    timing: str
    target_date: str
    fertilizer_type: str
    amount_kg_per_hectare: float
    total_amount_kg: float
    notes: str


# ========== SYSTEM ALERT (data pipeline monitoring + alerts) ==========
class SystemAlertCreate(BaseModel):
    """Create payload for SystemAlert."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "farm_id": 1,
                "field_id": None,
                "alert_type": "sensor_anomaly",
                "severity": "medium",
                "message": "Sensör #5 son 2 saatte veri göndermiyor — pil veya bağlantı kontrolü gerek.",
            }
        }
    )

    farm_id: int | None = None
    field_id: int | None = None
    alert_type: str  # 'sensor_anomaly' | 'weather_warning' | 'system_error' | ...
    severity: str = "low"  # 'low' | 'medium' | 'critical'
    message: str


class SystemAlertResponse(BaseModel):
    """SystemAlert serializer (response shape)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    farm_id: int | None
    field_id: int | None
    alert_type: str
    severity: str
    message: str
    is_resolved: bool
    created_at: UtcDateTime


class SystemAlertUpdate(BaseModel):
    """Alert'in resolved durumunu güncellemek icin kismi update."""

    is_resolved: bool | None = None
    severity: str | None = None
    message: str | None = None


# ========== MODEL PERFORMANCE LOG (ML model performance tracking) ==========
class ModelPerformanceLogCreate(BaseModel):
    """Create payload for ModelPerformanceLog."""

    model_name: str  # 'irrigation_rf' | 'plant_disease_cnn' | ...
    prediction_data: str  # JSON serialized
    actual_data: str | None = None
    accuracy_score: float | None = None


class ModelPerformanceLogResponse(BaseModel):
    """ModelPerformanceLog serializer (response shape)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    model_name: str
    prediction_data: str
    actual_data: str | None
    accuracy_score: float | None
    logged_at: UtcDateTime


class ModelPerformanceSummary(BaseModel):
    """Bir modelin agregat performans ozeti."""

    model_name: str
    total_predictions: int
    avg_accuracy: float | None
    last_logged: UtcDateTime | None


class ModelPerformanceLogUpdate(BaseModel):
    """Log oluşturulduktan sonra gerçek değer + accuracy doldurma için kısmi update."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "actual_data": '{"actual_water_liters": 30.0}',
                "accuracy_score": 0.92,
            }
        }
    )

    actual_data: str | None = None
    accuracy_score: float | None = None


class ModelPerformanceTimeseriesPoint(BaseModel):
    """Zaman serisi tek günlük accuracy ortalaması."""

    date: str  # YYYY-MM-DD
    avg_accuracy: float | None
    count: int


class ModelPerformanceDriftReport(BaseModel):
    """Model drift raporu — son periyot vs önceki periyot accuracy karşılaştırması."""

    model_name: str
    recent_avg_accuracy: float | None
    baseline_avg_accuracy: float | None
    drift_percent: float | None  # negatif = düşüş (drift), pozitif = iyileşme
    drift_detected: bool
    threshold_percent: float
    recent_window_days: int
    baseline_window_days: int
    alert_created: bool


class ModelPerformanceCompareItem(BaseModel):
    """Compare endpoint'i için tek model özet satırı."""

    model_name: str
    total_predictions: int
    avg_accuracy: float | None
    min_accuracy: float | None
    max_accuracy: float | None
    last_logged: UtcDateTime | None


# ========== HEALTH (deep health check) ==========
class HealthCheckResponse(BaseModel):
    """Detayli sistem sagligi raporu."""

    status: str  # 'healthy' | 'degraded' | 'unhealthy'
    service: str
    version: str
    components: dict  # {db: ok, scheduler: ok, ml_model: ok, ...}
    timestamp: UtcDateTime
