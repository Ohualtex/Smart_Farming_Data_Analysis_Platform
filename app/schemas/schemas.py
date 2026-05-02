from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ========== USER ==========
class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "farmer"
    phone: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str
    created_at: datetime


# ========== FARM ==========
class FarmCreate(BaseModel):
    name: str
    location_lat: float | None = None
    location_lng: float | None = None
    area_hectares: float | None = None
    city: str | None = None
    region: str | None = None


class FarmResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    location_lat: float | None
    location_lng: float | None
    area_hectares: float | None
    city: str | None
    region: str | None


# ========== FIELD ==========
class FieldCreate(BaseModel):
    name: str
    area_hectares: float | None = None
    soil_type: str | None = None
    elevation_m: float | None = None


class FieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    farm_id: int
    name: str
    area_hectares: float | None
    soil_type: str | None


# ========== SENSOR ==========
class SensorCreate(BaseModel):
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
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_id: int
    sensor_type: str
    serial_number: str
    status: str


# ========== SENSOR READING ==========
class SensorReadingCreate(BaseModel):
    sensor_id: int
    moisture_percent: float
    depth_cm: float | None = None
    soil_temperature_c: float | None = None
    electrical_conductivity: float | None = None


class SensorReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sensor_id: int
    reading_timestamp: datetime
    moisture_percent: float
    soil_temperature_c: float | None


# ========== WEATHER ==========
class WeatherDataCreate(BaseModel):
    farm_id: int
    temperature_c: float | None = None
    humidity_percent: float | None = None
    precipitation_mm: float | None = None
    wind_speed_kmh: float | None = None


class WeatherDataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    farm_id: int | None
    recorded_at: datetime
    temperature_c: float | None
    humidity_percent: float | None
    precipitation_mm: float | None


# ========== IRRIGATION ==========
class IrrigationCreate(BaseModel):
    field_id: int
    scheduled_date: datetime
    duration_min: int | None = None
    water_amount_liters: float | None = None


class IrrigationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_id: int
    scheduled_date: datetime
    water_amount_liters: float | None
    status: str


class IrrigationPredictionRequest(BaseModel):
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

    soil_moisture: float  # %0-100 toprak nemi
    soil_temperature: float  # °C
    humidity: float  # %0-100 hava nemi
    temperature: float  # °C hava sıcaklığı
    precipitation: float  # son 24 saat yağış (mm)


class IrrigationPredictionResponse(BaseModel):
    recommended_water_liters: float
    irrigation_needed: bool
    confidence: float
    message: str


# ========== FERTILIZER (Gübreleme) ==========
class FertilizerRecommendRequest(BaseModel):
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
    crop_type: str
    planting_date: str  # YYYY-MM-DD
    area_hectares: float
    soil_nitrogen: float = 0.0
    soil_phosphorus: float = 0.0
    soil_potassium: float = 0.0


class FertilizerScheduleResponse(BaseModel):
    phase: str
    timing: str
    target_date: str
    fertilizer_type: str
    amount_kg_per_hectare: float
    total_amount_kg: float
    notes: str


# ========== SOIL ANALYSIS (Toprak Analizi) ==========
class SoilAnalysisCreate(BaseModel):
    field_id: int
    ph_level: float | None = None
    organic_matter_pct: float | None = None
    nitrogen_mg_kg: float | None = None
    phosphorus_mg_kg: float | None = None
    potassium_mg_kg: float | None = None
    calcium_mg_kg: float | None = None
    magnesium_mg_kg: float | None = None
    texture_class: str | None = None
    notes: str | None = None


class SoilAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_id: int
    analysis_date: datetime
    ph_level: float | None
    organic_matter_pct: float | None
    nitrogen_mg_kg: float | None
    phosphorus_mg_kg: float | None
    potassium_mg_kg: float | None
    texture_class: str | None


# ========== CROP PLANTING (Ekim Takibi) ==========
class CropPlantingCreate(BaseModel):
    field_id: int
    crop_id: int
    planting_date: datetime
    expected_harvest_date: datetime | None = None
    season: str | None = None


class CropPlantingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_id: int
    crop_id: int
    planting_date: datetime
    expected_harvest_date: datetime | None
    season: str | None
    yield_kg_per_hectare: float | None
    status: str


# ========== FERTILIZER RECOMMENDATION LOG ==========
class FertilizerRecommendationLogCreate(BaseModel):
    field_id: int
    crop_id: int
    nitrogen_kg: float
    phosphorus_kg: float
    potassium_kg: float
    total_fertilizer_kg: float
    recommendation_text: str | None = None


class FertilizerRecommendationLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_id: int
    crop_id: int
    recommended_at: datetime
    nitrogen_kg: float
    phosphorus_kg: float
    potassium_kg: float
    total_fertilizer_kg: float
    is_applied: bool


# ========== SYSTEM ALERT (Ecenur — Cycle 6: Veri hatti izleme & uyari) ==========
class SystemAlertCreate(BaseModel):
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
    model_config = ConfigDict(from_attributes=True)

    id: int
    farm_id: int | None
    field_id: int | None
    alert_type: str
    severity: str
    message: str
    is_resolved: bool
    created_at: datetime


class SystemAlertUpdate(BaseModel):
    """Alert'in resolved durumunu güncellemek icin kismi update."""

    is_resolved: bool | None = None
    severity: str | None = None
    message: str | None = None


# ========== MODEL PERFORMANCE LOG (Mehmet — Cycle 6: Model perf izleme) ==========
class ModelPerformanceLogCreate(BaseModel):
    model_name: str  # 'irrigation_rf' | 'plant_disease_cnn' | ...
    prediction_data: str  # JSON serialized
    actual_data: str | None = None
    accuracy_score: float | None = None


class ModelPerformanceLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_name: str
    prediction_data: str
    actual_data: str | None
    accuracy_score: float | None
    logged_at: datetime


class ModelPerformanceSummary(BaseModel):
    """Bir modelin agregat performans ozeti."""

    model_name: str
    total_predictions: int
    avg_accuracy: float | None
    last_logged: datetime | None


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


class ModelPerformanceCompareItem(BaseModel):
    """Compare endpoint'i için tek model özet satırı."""

    model_name: str
    total_predictions: int
    avg_accuracy: float | None
    min_accuracy: float | None
    max_accuracy: float | None
    last_logged: datetime | None


# ========== HEALTH (Mehmet — Cycle 6: deep health check) ==========
class HealthCheckResponse(BaseModel):
    """Detayli sistem sagligi raporu."""

    status: str  # 'healthy' | 'degraded' | 'unhealthy'
    service: str
    version: str
    components: dict  # {db: ok, scheduler: ok, ml_model: ok, ...}
    timestamp: datetime
