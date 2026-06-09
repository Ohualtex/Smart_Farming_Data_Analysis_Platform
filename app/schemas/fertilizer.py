"""Gübreleme Pydantic şemaları."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    # Negatif/sıfır alan → negatif gübre kg veya yanlış "toprak yeterli" sonucu
    # (audit YÜKSEK). gt=0 ile Pydantic 422 döner, servis hiç çalışmaz.
    area_hectares: float = Field(..., gt=0.0)


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
    area_hectares: float = Field(..., gt=0.0)  # negatif/sıfır alan reddedilir (audit YÜKSEK)
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
