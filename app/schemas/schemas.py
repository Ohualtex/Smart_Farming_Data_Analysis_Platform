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
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator


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

# SQLite INTEGER is signed 64-bit: max = 2**63 - 1 = 9_223_372_036_854_775_807.
# Without this bound Schemathesis / hand-crafted clients can submit ints
# beyond that and trip an OverflowError → 500 inside SQLAlchemy's
# `do_execute`. With the bound Pydantic returns 422 cleanly.
# Mirrors the Query-side `MAX_SKIP` guard added in `7e49bef` for skip/limit;
# this is the body-side companion (caught by POST /api/weather/ fuzz).
SQLITE_INT_MAX = 9_223_372_036_854_775_807
SqliteSafeInt = Annotated[int, Field(le=SQLITE_INT_MAX, ge=-SQLITE_INT_MAX - 1)]


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

    field_id: SqliteSafeInt
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

    sensor_id: SqliteSafeInt
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

    farm_id: SqliteSafeInt
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

    field_id: SqliteSafeInt
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


class IrrigationStatusUpdate(BaseModel):
    """Sulama programı durum güncelleme — REBUILD Faz 4 onay/takip akışı.

    pending (öneri onaylandı, bekliyor) → completed (yapıldı) | cancelled (iptal).
    """

    model_config = ConfigDict(json_schema_extra={"example": {"status": "completed"}})

    status: Literal["pending", "completed", "cancelled"]


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

    @field_validator("planting_date")
    @classmethod
    def _validate_planting_date(cls, value: str) -> str:
        """`planting_date` 'YYYY-MM-DD' formatinda olmali (fail-fast 422).

        Bos string veya gecersiz tarih burada Pydantic ValidationError
        (422) tetikler. Aksi halde `fertilizer_service.generate_schedule`
        icindeki `datetime.strptime(planting_date, ...)` ham `ValueError`
        firlatip 500 donerdi (Schemathesis fuzz bulgusu: POST
        /api/fertilizer/schedules, planting_date="").
        """
        try:
            datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)
        except ValueError as exc:
            raise ValueError("planting_date 'YYYY-MM-DD' formatinda olmali") from exc
        return value


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

    farm_id: SqliteSafeInt | None = None
    field_id: SqliteSafeInt | None = None
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


# ========== FARM / FIELD / SOIL (Cycle 9 GET endpoint'leri) ==========
class FieldSummary(BaseModel):
    """Field özet — `FarmDetailResponse.fields` içinde nested olarak döner."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    area_hectares: float | None = None
    soil_type: str | None = None
    elevation_m: float | None = None
    crop_id: int | None = None


class FarmResponse(BaseModel):
    """Farm liste yanıtı (`GET /api/farms/`)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    city: str | None = None
    region: str | None = None
    area_hectares: float | None = None
    location_lat: float | None = None
    location_lng: float | None = None


class FarmDetailResponse(FarmResponse):
    """Farm detay yanıtı (`GET /api/farms/{farm_id}`) — `fields` nested."""

    fields: list[FieldSummary]


# ========== FARM / FIELD WRITE (REBUILD Faz 4 — CRUD) ==========
class FarmCreate(BaseModel):
    """Yeni çiftlik oluşturma — `user_id` current_user'dan alınır (body'de yok)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Ahmet'in Çiftliği",
                "city": "Konya",
                "region": "İç Anadolu",
                "area_hectares": 8.0,
                "location_lat": 37.87,
                "location_lng": 32.48,
            }
        }
    )

    name: str
    city: str | None = None
    region: str | None = None
    area_hectares: float | None = None
    location_lat: float | None = None
    location_lng: float | None = None


class FarmUpdate(BaseModel):
    """Çiftlik kısmi güncelleme — yalnız verilen alanlar değişir (exclude_unset)."""

    name: str | None = None
    city: str | None = None
    region: str | None = None
    area_hectares: float | None = None
    location_lat: float | None = None
    location_lng: float | None = None


class FieldCreate(BaseModel):
    """Yeni tarla oluşturma — `farm_id` sahiplik kontrolünden geçer."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "farm_id": 1,
                "name": "Tarla A",
                "soil_type": "killi",
                "area_hectares": 3.5,
                "elevation_m": 1020.0,
                "crop_id": 1,
            }
        }
    )

    farm_id: SqliteSafeInt
    name: str
    soil_type: str | None = None
    area_hectares: float | None = None
    elevation_m: float | None = None
    crop_id: SqliteSafeInt | None = None


class FieldUpdate(BaseModel):
    """Tarla kısmi güncelleme — yalnız verilen alanlar değişir."""

    name: str | None = None
    soil_type: str | None = None
    area_hectares: float | None = None
    elevation_m: float | None = None
    crop_id: SqliteSafeInt | None = None


class SoilAnalysisResponse(BaseModel):
    """SoilAnalysis serializer (`GET /api/farms/{farm_id}/soil`)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    field_id: int
    analysis_date: UtcDateTime
    ph_level: float | None = None
    organic_matter_pct: float | None = None
    nitrogen_mg_kg: float | None = None
    phosphorus_mg_kg: float | None = None
    potassium_mg_kg: float | None = None
    calcium_mg_kg: float | None = None
    magnesium_mg_kg: float | None = None
    texture_class: str | None = None
    notes: str | None = None


# ========== HEALTH (deep health check) ==========
class HealthCheckResponse(BaseModel):
    """Detayli sistem sagligi raporu."""

    status: str  # 'healthy' | 'degraded' | 'unhealthy'
    service: str
    version: str
    components: dict  # {db: ok, scheduler: ok, ml_model: ok, ...}
    timestamp: UtcDateTime


# ========== DASHBOARD (REBUILD Faz 2 — rol-aware "Çiftliğim") ==========
class DashboardSoilMoisture(BaseModel):
    """Son 24 saat içindeki toprak nemi özeti.

    Farmer rolü için kendi sensörlerinden, admin/overseer/developer için
    sistem-geneli sensörlerden hesaplanır.
    """

    avg_moisture_percent: float | None = None
    reading_count: int = 0
    sensor_count: int = 0
    last_reading_at: UtcDateTime | None = None
    status: str = "no_data"  # 'dry' | 'optimal' | 'wet' | 'no_data'


class DashboardLastIrrigation(BaseModel):
    """En son planlanan/gerçekleşen sulama kaydı."""

    irrigation_id: int | None = None
    field_id: int | None = None
    field_name: str | None = None
    scheduled_date: UtcDateTime | None = None
    water_amount_liters: float | None = None
    status: str | None = None  # 'scheduled' | 'completed' | 'cancelled' | ...


class DashboardOpenAlerts(BaseModel):
    """Açık (resolved=False) uyarı sayımı + severity kırılımı."""

    total: int = 0
    by_severity: dict[str, int] = Field(default_factory=lambda: {"low": 0, "medium": 0, "critical": 0})
    latest_message: str | None = None
    latest_severity: str | None = None
    latest_created_at: UtcDateTime | None = None


class DashboardLastDisease(BaseModel):
    """En son bitki sağlığı tanısı (CNN/heuristic tahmin)."""

    image_id: int | None = None
    field_id: int | None = None
    field_name: str | None = None
    captured_at: UtcDateTime | None = None
    diagnosis: str | None = None
    severity: str | None = None  # 'none' | 'mild' | 'moderate' | 'severe'
    confidence_score: float | None = None


class DashboardSummaryResponse(BaseModel):
    """Rol-aware 'Çiftliğim' özet ekranı.

    `scope == 'user'`: farmer rolü, yalnız kendi farm zinciri.
    `scope == 'system'`: admin/overseer/developer, sistem-geneli toplam.
    """

    user_name: str
    user_role: str  # 'farmer' | 'developer' | 'overseer' | 'admin'
    scope: str  # 'user' | 'system'
    farm_count: int
    field_count: int
    sensor_count: int
    soil_moisture_today: DashboardSoilMoisture
    last_irrigation: DashboardLastIrrigation
    open_alerts: DashboardOpenAlerts
    last_disease: DashboardLastDisease
    generated_at: UtcDateTime


# ========== FIELD DETAIL (REBUILD Faz 3 — Tarla detay sayfası) ==========
class FieldCropInfo(BaseModel):
    """Tarlaya ekili bitki türü özeti (CropType)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    scientific_name: str | None = None
    water_need_mm_per_day: float | None = None


class FieldSensorSummary(BaseModel):
    """Tarladaki tek sensör + en son okuması (detay sayfası kartı için)."""

    id: int
    sensor_type: str
    serial_number: str | None = None
    status: str
    latest_moisture_percent: float | None = None
    latest_soil_temperature_c: float | None = None
    latest_reading_at: UtcDateTime | None = None


class FieldIrrigationSummary(BaseModel):
    """Tarlanın sulama geçmişinden tek kayıt."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    scheduled_date: UtcDateTime
    water_amount_liters: float | None = None
    duration_min: int | None = None
    status: str
    source: str | None = None


class FieldDiseaseSummary(BaseModel):
    """Tarlanın bitki sağlığı/hastalık geçmişinden tek kayıt."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str | None = None
    captured_at: UtcDateTime | None = None
    diagnosis: str | None = None
    confidence_score: float | None = None
    severity: str | None = None


class FieldAlertSummary(BaseModel):
    """Tarlaya bağlı açık uyarı (SystemAlert)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_type: str
    severity: str
    message: str
    is_resolved: bool
    created_at: UtcDateTime


class FieldDetailResponse(BaseModel):
    """Tek tarlanın tüm bağlamı — sensör, sulama, hastalık, toprak, uyarı.

    Demo akışının kalbi: dashboard "Tarla A susuz" → bu sayfa → yaprak
    foto upload → tanı. RBAC: farmer yalnız kendi tarlasını görür.
    """

    # ─── Tarla çekirdeği ───────────────────────────
    id: int
    name: str
    area_hectares: float | None = None
    soil_type: str | None = None
    elevation_m: float | None = None
    # ─── Üst çiftlik ───────────────────────────────
    farm_id: int
    farm_name: str
    region: str | None = None
    city: str | None = None
    # ─── Ekili bitki ───────────────────────────────
    crop: FieldCropInfo | None = None
    # ─── Toprak nemi özeti (son 24 saat, tarladaki sensörler) ──
    moisture_status: str  # 'dry' | 'optimal' | 'wet' | 'no_data'
    avg_moisture_percent: float | None = None
    # ─── Koleksiyonlar ─────────────────────────────
    sensors: list[FieldSensorSummary]
    recent_irrigations: list[FieldIrrigationSummary]
    disease_history: list[FieldDiseaseSummary]
    soil_analyses: list[SoilAnalysisResponse]
    open_alerts: list[FieldAlertSummary]
    generated_at: UtcDateTime
