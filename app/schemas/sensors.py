"""Sensör ve sensör okuma Pydantic şemaları."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schemas.base import SqliteSafeInt, UtcDateTime


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
