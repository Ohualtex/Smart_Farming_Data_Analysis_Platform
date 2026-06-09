from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base

# ─── RBAC (REBUILD Faz 1) ──────────────────────────────────────────
# 4 rollü access control — bkz. `docs/REBUILD_ROADMAP.md` Faz 1.
#   farmer    : kendi çiftliği/tarlası/sensörü; register default
#   developer : API key + Swagger + test endpoint'leri; admin promote eder
#   overseer  : tüm sistem read-only (analytics + harita); admin promote eder
#   admin     : tüm sistem + kullanıcı/rol yönetimi
# `role` field'ı için DB-side CHECK constraint Alembic migration ile gelir
# (Adım 2). Python tarafında Pydantic `Literal[...]` validation auth
# schema'larında çalışır (Adım 3-4).
USER_ROLES: tuple[str, ...] = ("farmer", "developer", "overseer", "admin")
DEFAULT_USER_ROLE = "farmer"


class User(Base):
    """ORM model for `users` table."""

    __tablename__ = "users"
    # RBAC bütünlüğü: `role` yalnız 4 geçerli değerden biri olabilir. Alembic
    # migration (b1c2d3e4f5a6) prod'da aynı CHECK'i kurar; model'de de tanımlı
    # olması create_all yolunun (dev/test) prod ile AYNI constraint'i üretmesini
    # sağlar (audit: iki şema yolu ayrışmasın).
    __table_args__ = (
        CheckConstraint(
            "role IN (" + ", ".join(f"'{_r}'" for _r in USER_ROLES) + ")",
            name="ck_users_role_valid",
        ),
    )
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    # 4-rol RBAC: USER_ROLES içinden biri. `index=True` farmer/admin
    # filter'larında full-scan'ı engeller; `server_default` PG/MySQL'de
    # mevcut satırlara da uygulanır (SQLite no-op, Alembic backfill ile
    # gelir — Adım 2).
    role = Column(
        String(20),
        nullable=False,
        default=DEFAULT_USER_ROLE,
        server_default=DEFAULT_USER_ROLE,
        index=True,
    )
    phone = Column(String(20))
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    farms = relationship("Farm", back_populates="owner")


class Farm(Base):
    """ORM model for `farms` table."""

    __tablename__ = "farms"
    id = Column(Integer, primary_key=True, index=True)
    # FK + index: farmer ownership filter (Farm.user_id == user.id) sık kullanılır
    # (RBAC scope_to_user). v3-5: index eklendi.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    location_lat = Column(Float)
    location_lng = Column(Float)
    area_hectares = Column(Float)
    city = Column(String(100))
    region = Column(String(100))
    owner = relationship("User", back_populates="farms")
    fields = relationship("Field", back_populates="farm")


class Field(Base):
    """ORM model for `fields` table."""

    __tablename__ = "fields"
    id = Column(Integer, primary_key=True, index=True)
    # FK + index: çiftliğin tarlaları (Field.farm_id == farm_id) sık filtre.
    # v3-5: index eklendi.
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    area_hectares = Column(Float)
    soil_type = Column(String(50))
    elevation_m = Column(Float)
    # FK + index: bitki türü join'i analytics'te kullanılır. v3-5: index eklendi.
    crop_id = Column(Integer, ForeignKey("crop_types.id"), index=True)
    farm = relationship("Farm", back_populates="fields")
    sensors = relationship("Sensor", back_populates="field")
    crop = relationship("CropType", back_populates="fields")


class CropType(Base):
    """ORM model for `crop_types` table."""

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
    fields = relationship("Field", back_populates="crop")


class Sensor(Base):
    """ORM model for `sensors` table."""

    __tablename__ = "sensors"
    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
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
    """ORM model for `soil_moisture_readings` table."""

    __tablename__ = "soil_moisture_readings"
    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    reading_timestamp = Column(DateTime, default=lambda: datetime.now(UTC), index=True)
    moisture_percent = Column(Float, nullable=False)
    depth_cm = Column(Float)
    soil_temperature_c = Column(Float)
    electrical_conductivity = Column(Float)
    sensor = relationship("Sensor", back_populates="readings")

    __table_args__ = (Index("ix_readings_sensor_timestamp", "sensor_id", "reading_timestamp"),)


class SensorReadingMonthlyAggregate(Base):
    """30 günden eski sensör okumalarının aylık özeti.

    `sensor_archiver.archive_old_readings` periyodik görevi tarafından
    doldurulur; orijinal `SoilMoistureReading` satırları aggregate'e
    yansıdıktan sonra silinir. (sensor_id, year, month) bazlı tek satır
    garantilidir (UniqueConstraint).

    EN: Monthly aggregate of soil-moisture readings older than 30 days.
    Populated by sensor_archiver.archive_old_readings; the source rows
    are deleted after a successful archive. Idempotent via the
    (sensor_id, year, month) unique constraint.
    """

    __tablename__ = "sensor_reading_monthly_aggregates"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)  # 1–12

    reading_count = Column(Integer, nullable=False)
    moisture_avg = Column(Float, nullable=False)
    moisture_min = Column(Float, nullable=False)
    moisture_max = Column(Float, nullable=False)
    soil_temperature_avg = Column(Float)
    soil_temperature_min = Column(Float)
    soil_temperature_max = Column(Float)
    electrical_conductivity_avg = Column(Float)

    archived_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    __table_args__ = (
        UniqueConstraint("sensor_id", "year", "month", name="uq_sensor_reading_aggregate_month"),
        Index("ix_sensor_reading_aggregate_year_month", "year", "month"),
    )


class WeatherData(Base):
    """ORM model for `weather_data` table."""

    __tablename__ = "weather_data"
    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"))
    recorded_at = Column(DateTime, default=lambda: datetime.now(UTC), index=True)
    temperature_c = Column(Float)
    humidity_percent = Column(Float)
    precipitation_mm = Column(Float)
    wind_speed_kmh = Column(Float)
    solar_radiation = Column(Float)
    uv_index = Column(Float)

    __table_args__ = (Index("ix_weather_farm_recorded", "farm_id", "recorded_at"),)


class IrrigationSchedule(Base):
    """ORM model for `irrigation_schedules` table."""

    __tablename__ = "irrigation_schedules"
    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    scheduled_date = Column(DateTime, nullable=False)
    duration_min = Column(Integer)
    water_amount_liters = Column(Float)
    source = Column(String(20), default="model")
    status = Column(String(20), default="pending")


class PlantHealthImage(Base):
    """ORM model for `plant_health_images` table."""

    __tablename__ = "plant_health_images"
    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"))
    image_url = Column(String(500))
    captured_at = Column(DateTime, default=lambda: datetime.now(UTC))
    diagnosis = Column(String(200))
    confidence_score = Column(Float)
    severity = Column(String(20))


class SystemAlert(Base):
    """ORM model for `system_alerts` table."""

    __tablename__ = "system_alerts"
    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=True, index=True)
    alert_type = Column(String(50), nullable=False)  # e.g., 'sensor_anomaly', 'weather_warning', 'system_error'
    severity = Column(String(20), default="low")  # 'low', 'medium', 'critical'
    message = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), index=True)


class ModelPerformanceLog(Base):
    """ORM model for `model_performance_logs` table."""

    __tablename__ = "model_performance_logs"
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False, index=True)  # e.g., 'irrigation_rf', 'plant_disease_cnn'
    prediction_data = Column(Text)  # JSON serialized
    actual_data = Column(Text, nullable=True)  # JSON serialized, filled later
    accuracy_score = Column(Float, nullable=True)
    logged_at = Column(DateTime, default=lambda: datetime.now(UTC), index=True)


class SoilAnalysis(Base):
    """ORM model for `soil_analyses` table."""

    __tablename__ = "soil_analyses"
    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    analysis_date = Column(DateTime, default=lambda: datetime.now(UTC))
    ph_level = Column(Float)
    organic_matter_pct = Column(Float)
    nitrogen_mg_kg = Column(Float)
    phosphorus_mg_kg = Column(Float)
    potassium_mg_kg = Column(Float)
    calcium_mg_kg = Column(Float)
    magnesium_mg_kg = Column(Float)
    texture_class = Column(String(50))  # e.g., 'killi-tınlı', 'kumlu', 'tınlı'
    notes = Column(Text, nullable=True)


class CropPlanting(Base):
    """ORM model for `crop_plantings` table."""

    __tablename__ = "crop_plantings"
    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    crop_id = Column(Integer, ForeignKey("crop_types.id"), nullable=False, index=True)
    planting_date = Column(DateTime, nullable=False)
    expected_harvest_date = Column(DateTime)
    actual_harvest_date = Column(DateTime, nullable=True)
    season = Column(String(20))  # e.g., '2025-2026', 'Yaz 2026'
    yield_kg_per_hectare = Column(Float, nullable=True)
    status = Column(String(20), default="growing")  # 'growing', 'harvested', 'failed'


class FertilizerRecommendationLog(Base):
    """ORM model for `fertilizer_recommendations` table."""

    __tablename__ = "fertilizer_recommendations"
    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    crop_id = Column(Integer, ForeignKey("crop_types.id"), nullable=False)
    recommended_at = Column(DateTime, default=lambda: datetime.now(UTC))
    nitrogen_kg = Column(Float)
    phosphorus_kg = Column(Float)
    potassium_kg = Column(Float)
    total_fertilizer_kg = Column(Float)
    recommendation_text = Column(Text)
    is_applied = Column(Boolean, default=False)
