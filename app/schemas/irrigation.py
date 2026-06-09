"""Sulama Pydantic şemaları."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.base import SqliteSafeInt, UtcDateTime


# ========== IRRIGATION ==========
class IrrigationCreate(BaseModel):
    """Create payload for Irrigation."""

    field_id: SqliteSafeInt
    scheduled_date: datetime
    # Audit düzeltmesi: negatif süre ve negatif/sıfır su miktarı reddedilir.
    duration_min: int | None = Field(None, ge=0)
    water_amount_liters: float | None = Field(None, gt=0)
    # Audit düzeltmesi: manuel program model default'u ('model') ile etiketlenmesin.
    source: str = "manual"


class IrrigationResponse(BaseModel):
    """Irrigation serializer (response shape)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    field_id: int
    scheduled_date: UtcDateTime
    # Audit düzeltmesi: frontend "Süre (dk)" kolonu için duration_min eksikti.
    duration_min: int | None
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
