"""Tarla detay sayfası Pydantic şemaları."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schemas.base import UtcDateTime
from app.schemas.farms import SoilAnalysisResponse


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
