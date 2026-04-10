from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


# ========== USER ==========
class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "farmer"
    phone: Optional[str] = None

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
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    area_hectares: Optional[float] = None
    city: Optional[str] = None
    region: Optional[str] = None

class FarmResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    location_lat: Optional[float]
    location_lng: Optional[float]
    area_hectares: Optional[float]
    city: Optional[str]
    region: Optional[str]


# ========== FIELD ==========
class FieldCreate(BaseModel):
    name: str
    area_hectares: Optional[float] = None
    soil_type: Optional[str] = None
    elevation_m: Optional[float] = None

class FieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    farm_id: int
    name: str
    area_hectares: Optional[float]
    soil_type: Optional[str]


# ========== SENSOR ==========
class SensorCreate(BaseModel):
    field_id: int
    sensor_type: str
    serial_number: str
    depth_cm: Optional[float] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

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
    depth_cm: Optional[float] = None
    soil_temperature_c: Optional[float] = None
    electrical_conductivity: Optional[float] = None

class SensorReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sensor_id: int
    reading_timestamp: datetime
    moisture_percent: float
    soil_temperature_c: Optional[float]


# ========== WEATHER ==========
class WeatherDataCreate(BaseModel):
    farm_id: int
    temperature_c: Optional[float] = None
    humidity_percent: Optional[float] = None
    precipitation_mm: Optional[float] = None
    wind_speed_kmh: Optional[float] = None

class WeatherDataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    farm_id: Optional[int]
    recorded_at: datetime
    temperature_c: Optional[float]
    humidity_percent: Optional[float]
    precipitation_mm: Optional[float]


# ========== IRRIGATION ==========
class IrrigationCreate(BaseModel):
    field_id: int
    scheduled_date: datetime
    duration_min: Optional[int] = None
    water_amount_liters: Optional[float] = None

class IrrigationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_id: int
    scheduled_date: datetime
    water_amount_liters: Optional[float]
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
