"""Sistem uyarısı Pydantic şemaları."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.base import SqliteSafeInt, UtcDateTime


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
    alert_type: str = Field(..., max_length=50)  # 'sensor_anomaly' | 'weather_warning' | ...
    # Audit düzeltmesi: keyfi severity değerleri dashboard/metrik kovalarını bozmasın.
    severity: Literal["low", "medium", "critical"] = "low"
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
    # Audit düzeltmesi: severity sadece geçerli kovalarla kısıtlandı.
    severity: Literal["low", "medium", "critical"] | None = None
    message: str | None = None
