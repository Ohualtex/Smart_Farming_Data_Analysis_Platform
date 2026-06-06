"""Model performans takip Pydantic şemaları."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schemas.base import UtcDateTime


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
