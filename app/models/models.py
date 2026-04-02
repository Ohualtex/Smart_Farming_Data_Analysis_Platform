from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="farmer")
    phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    farms = relationship("Farm", back_populates="owner")


class Farm(Base):
    __tablename__ = "farms"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(150), nullable=False)
    location_lat = Column(Float)
    location_lng = Column(Float)
    area_hectares = Column(Float)
    city = Column(String(100))
    region = Column(String(100))
    owner = relationship("User", back_populates="farms")
    fields = relationship("Field", back_populates="farm")


class Field(Base):
    __tablename__ = "fields"
    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    name = Column(String(150), nullable=False)
    area_hectares = Column(Float)
    soil_type = Column(String(50))
    elevation_m = Column(Float)
    farm = relationship("Farm", back_populates="fields")
    sensors = relationship("Sensor", back_populates="field")


class CropType(Base):
    __tablename__ = "crop_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    scientific_name = Column(String(150))
    optimal_ph_min = Column(Float)
    optimal_ph_max = Column(Float)
    optimal_temp_min = Column(Float)
    optimal_temp_max = Column(Float)
    water_need_mm_per_day = Column(Float)
    growth_duration_days = Column(Integer)


class Sensor(Base):
    __tablename__ = "sensors"
    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)
    sensor_type = Column(String(50), nullable=False)
    serial_number = Column(String(100), unique=True)
    installation_date = Column(DateTime)
    depth_cm = Column(Float)
    lat = Column(Float)
    lng = Column(Float)
    status = Column(String(20), default="active")
    field = relationship("Field", back_populates="sensors")
    readings = relationship("SoilMoistureReading", back_populates="sensor")


class SoilMoistureReading(Base):
    __tablename__ = "soil_moisture_readings"
    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    reading_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    moisture_percent = Column(Float, nullable=False)
    depth_cm = Column(Float)
    soil_temperature_c = Column(Float)
    electrical_conductivity = Column(Float)
    sensor = relationship("Sensor", back_populates="readings")


class WeatherData(Base):
    __tablename__ = "weather_data"
    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"))
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    temperature_c = Column(Float)
    humidity_percent = Column(Float)
    precipitation_mm = Column(Float)
    wind_speed_kmh = Column(Float)
    solar_radiation = Column(Float)
    uv_index = Column(Float)


class IrrigationSchedule(Base):
    __tablename__ = "irrigation_schedules"
    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)
    scheduled_date = Column(DateTime, nullable=False)
    duration_min = Column(Integer)
    water_amount_liters = Column(Float)
    source = Column(String(20), default="model")
    status = Column(String(20), default="pending")


class PlantHealthImage(Base):
    __tablename__ = "plant_health_images"
    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"))
    image_url = Column(String(500))
    captured_at = Column(DateTime, default=datetime.utcnow)
    diagnosis = Column(String(200))
    confidence_score = Column(Float)
    severity = Column(String(20))
