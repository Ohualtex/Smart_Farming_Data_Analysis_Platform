"""Dashboard ('Çiftliğim') özet Pydantic şemaları."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.base import UtcDateTime


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
