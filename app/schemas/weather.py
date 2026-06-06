"""Hava durumu Pydantic şemaları."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schemas.base import SqliteSafeInt, UtcDateTime


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
