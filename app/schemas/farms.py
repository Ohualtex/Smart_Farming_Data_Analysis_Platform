"""Çiftlik / tarla / toprak Pydantic şemaları."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.base import SqliteSafeInt, UtcDateTime

# NOT: max_length DB kolon uzunluklarıyla hizalı (User/Farm/Field). Aksi halde
# aşırı-uzun string SQLite'ta geçer ama PostgreSQL'de 500 (StringDataRightTruncation)
# verirdi (audit YÜKSEK: SQLite↔PG ayrışması). Burada Pydantic 422 ile erken döner.


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

    name: str = Field(..., max_length=150)
    city: str | None = Field(None, max_length=100)
    region: str | None = Field(None, max_length=100)
    area_hectares: float | None = None
    location_lat: float | None = None
    location_lng: float | None = None


class FarmUpdate(BaseModel):
    """Çiftlik kısmi güncelleme — yalnız verilen alanlar değişir (exclude_unset)."""

    name: str | None = Field(None, max_length=150)
    city: str | None = Field(None, max_length=100)
    region: str | None = Field(None, max_length=100)
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
    name: str = Field(..., max_length=150)
    soil_type: str | None = Field(None, max_length=50)
    area_hectares: float | None = None
    elevation_m: float | None = None
    crop_id: SqliteSafeInt | None = None


class FieldUpdate(BaseModel):
    """Tarla kısmi güncelleme — yalnız verilen alanlar değişir."""

    name: str | None = Field(None, max_length=150)
    soil_type: str | None = Field(None, max_length=50)
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
