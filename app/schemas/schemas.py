from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ========== USER ==========
class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "farmer"
    phone: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str
    created_at: datetime


# ========== FARM ==========
class FarmCreate(BaseModel):
    name: str
    location_lat: float | None = None
    location_lng: float | None = None
    area_hectares: float | None = None
    city: str | None = None
    region: str | None = None


class FarmResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    location_lat: float | None
    location_lng: float | None
    area_hectares: float | None
    city: str | None
    region: str | None


# ========== FIELD ==========
class FieldCreate(BaseModel):
    name: str
    area_hectares: float | None = None
    soil_type: str | None = None
    elevation_m: float | None = None


class FieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    farm_id: int
    name: str
    area_hectares: float | None
    soil_type: str | None


# ========== SENSOR ==========
class SensorCreate(BaseModel):
    field_id: int
    sensor_type: str
    serial_number: str
    depth_cm: float | None = None
    lat: float | None = None
    lng: float | None = None


class SensorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_id: int
    sensor_type: str
    serial_number: str
    status: str


# ========== SENSOR READING ==========
class SensorReadingCreate(BaseModel):
    sensor_id: int
    moisture_percent: float
    depth_cm: float | None = None
    soil_temperature_c: float | None = None
    electrical_conductivity: float | None = None


class SensorReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sensor_id: int
    reading_timestamp: datetime
    moisture_percent: float
    soil_temperature_c: float | None


# ========== WEATHER ==========
class WeatherDataCreate(BaseModel):
    farm_id: int
    temperature_c: float | None = None
    humidity_percent: float | None = None
    precipitation_mm: float | None = None
    wind_speed_kmh: float | None = None


class WeatherDataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    farm_id: int | None
    recorded_at: datetime
    temperature_c: float | None
    humidity_percent: float | None
    precipitation_mm: float | None


# ========== IRRIGATION ==========
class IrrigationCreate(BaseModel):
    field_id: int
    scheduled_date: datetime
    duration_min: int | None = None
    water_amount_liters: float | None = None


class IrrigationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_id: int
    scheduled_date: datetime
    water_amount_liters: float | None
    status: str


class IrrigationPredictionRequest(BaseModel):
    soil_moisture: float
    soil_temperature: float
    humidity: float
    temperature: float
    precipitation: float


class IrrigationPredictionResponse(BaseModel):
    recommended_water_liters: float
    irrigation_needed: bool
    confidence: float
    message: str


# ========== FERTILIZER (Gübreleme) ==========
class FertilizerRecommendRequest(BaseModel):
    crop_type: str
    soil_nitrogen: float  # mg/kg
    soil_phosphorus: float  # mg/kg
    soil_potassium: float  # mg/kg
    area_hectares: float


class FertilizerRecommendResponse(BaseModel):
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
    crop_type: str
    planting_date: str  # YYYY-MM-DD
    area_hectares: float
    soil_nitrogen: float = 0.0
    soil_phosphorus: float = 0.0
    soil_potassium: float = 0.0


class FertilizerScheduleResponse(BaseModel):
    phase: str
    timing: str
    target_date: str
    fertilizer_type: str
    amount_kg_per_hectare: float
    total_amount_kg: float
    notes: str
