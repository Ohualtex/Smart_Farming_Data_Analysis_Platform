"""Sistem uyarısı Pydantic şemaları."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

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
