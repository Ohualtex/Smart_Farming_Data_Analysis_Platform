-- ============================================================
-- SFDAP Database Schema (auto-generated from Alembic head)
-- ============================================================
-- Bu dosya 'alembic upgrade head' cikti'sinin SQL dump'idir.
-- Generated: 2026-06-06 19:18 UTC
-- Regenerate: make schema-dump
-- ============================================================

CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL,
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
CREATE TABLE crop_types (
	id INTEGER NOT NULL,
	name VARCHAR(100) NOT NULL,
	scientific_name VARCHAR(150),
	optimal_ph_min FLOAT,
	optimal_ph_max FLOAT,
	optimal_temp_min FLOAT,
	optimal_temp_max FLOAT,
	water_need_mm_per_day FLOAT,
	growth_duration_days INTEGER,
	CONSTRAINT pk_crop_types PRIMARY KEY (id)
);
CREATE INDEX ix_crop_types_id ON crop_types (id);
CREATE TABLE model_performance_logs (
	id INTEGER NOT NULL,
	model_name VARCHAR(100) NOT NULL,
	prediction_data TEXT,
	actual_data TEXT,
	accuracy_score FLOAT,
	logged_at DATETIME,
	CONSTRAINT pk_model_performance_logs PRIMARY KEY (id)
);
CREATE INDEX ix_model_performance_logs_id ON model_performance_logs (id);
CREATE INDEX ix_model_performance_logs_logged_at ON model_performance_logs (logged_at);
CREATE INDEX ix_model_performance_logs_model_name ON model_performance_logs (model_name);
CREATE TABLE farms (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	name VARCHAR(150) NOT NULL,
	location_lat FLOAT,
	location_lng FLOAT,
	area_hectares FLOAT,
	city VARCHAR(100),
	region VARCHAR(100),
	CONSTRAINT pk_farms PRIMARY KEY (id),
	CONSTRAINT fk_farms_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_farms_id ON farms (id);
CREATE TABLE fields (
	id INTEGER NOT NULL,
	farm_id INTEGER NOT NULL,
	name VARCHAR(150) NOT NULL,
	area_hectares FLOAT,
	soil_type VARCHAR(50),
	elevation_m FLOAT,
	crop_id INTEGER,
	CONSTRAINT pk_fields PRIMARY KEY (id),
	CONSTRAINT fk_fields_crop_id_crop_types FOREIGN KEY(crop_id) REFERENCES crop_types (id),
	CONSTRAINT fk_fields_farm_id_farms FOREIGN KEY(farm_id) REFERENCES farms (id)
);
CREATE INDEX ix_fields_id ON fields (id);
CREATE TABLE weather_data (
	id INTEGER NOT NULL,
	farm_id INTEGER,
	recorded_at DATETIME,
	temperature_c FLOAT,
	humidity_percent FLOAT,
	precipitation_mm FLOAT,
	wind_speed_kmh FLOAT,
	solar_radiation FLOAT,
	uv_index FLOAT,
	CONSTRAINT pk_weather_data PRIMARY KEY (id),
	CONSTRAINT fk_weather_data_farm_id_farms FOREIGN KEY(farm_id) REFERENCES farms (id)
);
CREATE INDEX ix_weather_data_id ON weather_data (id);
CREATE INDEX ix_weather_data_recorded_at ON weather_data (recorded_at);
CREATE INDEX ix_weather_farm_recorded ON weather_data (farm_id, recorded_at);
CREATE TABLE crop_plantings (
	id INTEGER NOT NULL,
	field_id INTEGER NOT NULL,
	crop_id INTEGER NOT NULL,
	planting_date DATETIME NOT NULL,
	expected_harvest_date DATETIME,
	actual_harvest_date DATETIME,
	season VARCHAR(20),
	yield_kg_per_hectare FLOAT,
	status VARCHAR(20),
	CONSTRAINT pk_crop_plantings PRIMARY KEY (id),
	CONSTRAINT fk_crop_plantings_crop_id_crop_types FOREIGN KEY(crop_id) REFERENCES crop_types (id),
	CONSTRAINT fk_crop_plantings_field_id_fields FOREIGN KEY(field_id) REFERENCES fields (id)
);
CREATE INDEX ix_crop_plantings_crop_id ON crop_plantings (crop_id);
CREATE INDEX ix_crop_plantings_field_id ON crop_plantings (field_id);
CREATE INDEX ix_crop_plantings_id ON crop_plantings (id);
CREATE TABLE fertilizer_recommendations (
	id INTEGER NOT NULL,
	field_id INTEGER NOT NULL,
	crop_id INTEGER NOT NULL,
	recommended_at DATETIME,
	nitrogen_kg FLOAT,
	phosphorus_kg FLOAT,
	potassium_kg FLOAT,
	total_fertilizer_kg FLOAT,
	recommendation_text TEXT,
	is_applied BOOLEAN,
	CONSTRAINT pk_fertilizer_recommendations PRIMARY KEY (id),
	CONSTRAINT fk_fertilizer_recommendations_crop_id_crop_types FOREIGN KEY(crop_id) REFERENCES crop_types (id),
	CONSTRAINT fk_fertilizer_recommendations_field_id_fields FOREIGN KEY(field_id) REFERENCES fields (id)
);
CREATE INDEX ix_fertilizer_recommendations_field_id ON fertilizer_recommendations (field_id);
CREATE INDEX ix_fertilizer_recommendations_id ON fertilizer_recommendations (id);
CREATE TABLE irrigation_schedules (
	id INTEGER NOT NULL,
	field_id INTEGER NOT NULL,
	scheduled_date DATETIME NOT NULL,
	duration_min INTEGER,
	water_amount_liters FLOAT,
	source VARCHAR(20),
	status VARCHAR(20),
	CONSTRAINT pk_irrigation_schedules PRIMARY KEY (id),
	CONSTRAINT fk_irrigation_schedules_field_id_fields FOREIGN KEY(field_id) REFERENCES fields (id)
);
CREATE INDEX ix_irrigation_schedules_field_id ON irrigation_schedules (field_id);
CREATE INDEX ix_irrigation_schedules_id ON irrigation_schedules (id);
CREATE TABLE plant_health_images (
	id INTEGER NOT NULL,
	field_id INTEGER,
	image_url VARCHAR(500),
	captured_at DATETIME,
	diagnosis VARCHAR(200),
	confidence_score FLOAT,
	severity VARCHAR(20),
	CONSTRAINT pk_plant_health_images PRIMARY KEY (id),
	CONSTRAINT fk_plant_health_images_field_id_fields FOREIGN KEY(field_id) REFERENCES fields (id)
);
CREATE INDEX ix_plant_health_images_id ON plant_health_images (id);
CREATE TABLE sensors (
	id INTEGER NOT NULL,
	field_id INTEGER NOT NULL,
	sensor_type VARCHAR(50) NOT NULL,
	serial_number VARCHAR(100),
	installation_date DATETIME,
	depth_cm FLOAT,
	lat FLOAT,
	lng FLOAT,
	status VARCHAR(20),
	CONSTRAINT pk_sensors PRIMARY KEY (id),
	CONSTRAINT fk_sensors_field_id_fields FOREIGN KEY(field_id) REFERENCES fields (id),
	CONSTRAINT uq_sensors_serial_number UNIQUE (serial_number)
);
CREATE INDEX ix_sensors_field_id ON sensors (field_id);
CREATE INDEX ix_sensors_id ON sensors (id);
CREATE TABLE soil_analyses (
	id INTEGER NOT NULL,
	field_id INTEGER NOT NULL,
	analysis_date DATETIME,
	ph_level FLOAT,
	organic_matter_pct FLOAT,
	nitrogen_mg_kg FLOAT,
	phosphorus_mg_kg FLOAT,
	potassium_mg_kg FLOAT,
	calcium_mg_kg FLOAT,
	magnesium_mg_kg FLOAT,
	texture_class VARCHAR(50),
	notes TEXT,
	CONSTRAINT pk_soil_analyses PRIMARY KEY (id),
	CONSTRAINT fk_soil_analyses_field_id_fields FOREIGN KEY(field_id) REFERENCES fields (id)
);
CREATE INDEX ix_soil_analyses_field_id ON soil_analyses (field_id);
CREATE INDEX ix_soil_analyses_id ON soil_analyses (id);
CREATE TABLE system_alerts (
	id INTEGER NOT NULL,
	farm_id INTEGER,
	field_id INTEGER,
	alert_type VARCHAR(50) NOT NULL,
	severity VARCHAR(20),
	message TEXT NOT NULL,
	is_resolved BOOLEAN,
	created_at DATETIME,
	CONSTRAINT pk_system_alerts PRIMARY KEY (id),
	CONSTRAINT fk_system_alerts_farm_id_farms FOREIGN KEY(farm_id) REFERENCES farms (id),
	CONSTRAINT fk_system_alerts_field_id_fields FOREIGN KEY(field_id) REFERENCES fields (id)
);
CREATE INDEX ix_system_alerts_created_at ON system_alerts (created_at);
CREATE INDEX ix_system_alerts_farm_id ON system_alerts (farm_id);
CREATE INDEX ix_system_alerts_field_id ON system_alerts (field_id);
CREATE INDEX ix_system_alerts_id ON system_alerts (id);
CREATE TABLE soil_moisture_readings (
	id INTEGER NOT NULL,
	sensor_id INTEGER NOT NULL,
	reading_timestamp DATETIME,
	moisture_percent FLOAT NOT NULL,
	depth_cm FLOAT,
	soil_temperature_c FLOAT,
	electrical_conductivity FLOAT,
	CONSTRAINT pk_soil_moisture_readings PRIMARY KEY (id),
	CONSTRAINT fk_soil_moisture_readings_sensor_id_sensors FOREIGN KEY(sensor_id) REFERENCES sensors (id)
);
CREATE INDEX ix_readings_sensor_timestamp ON soil_moisture_readings (sensor_id, reading_timestamp);
CREATE INDEX ix_soil_moisture_readings_id ON soil_moisture_readings (id);
CREATE INDEX ix_soil_moisture_readings_reading_timestamp ON soil_moisture_readings (reading_timestamp);
CREATE TABLE sensor_reading_monthly_aggregates (
	id INTEGER NOT NULL,
	sensor_id INTEGER NOT NULL,
	year INTEGER NOT NULL,
	month INTEGER NOT NULL,
	reading_count INTEGER NOT NULL,
	moisture_avg FLOAT NOT NULL,
	moisture_min FLOAT NOT NULL,
	moisture_max FLOAT NOT NULL,
	soil_temperature_avg FLOAT,
	soil_temperature_min FLOAT,
	soil_temperature_max FLOAT,
	electrical_conductivity_avg FLOAT,
	archived_at DATETIME NOT NULL,
	CONSTRAINT pk_sensor_reading_monthly_aggregates PRIMARY KEY (id),
	CONSTRAINT fk_sensor_reading_monthly_aggregates_sensor_id_sensors FOREIGN KEY(sensor_id) REFERENCES sensors (id),
	CONSTRAINT uq_sensor_reading_aggregate_month UNIQUE (sensor_id, year, month)
);
CREATE INDEX ix_sensor_reading_aggregate_year_month ON sensor_reading_monthly_aggregates (year, month);
CREATE INDEX ix_sensor_reading_monthly_aggregates_id ON sensor_reading_monthly_aggregates (id);
CREATE INDEX ix_sensor_reading_monthly_aggregates_sensor_id ON sensor_reading_monthly_aggregates (sensor_id);
CREATE TABLE IF NOT EXISTS "users" (
	id INTEGER NOT NULL,
	name VARCHAR(100) NOT NULL,
	email VARCHAR(150) NOT NULL,
	password_hash VARCHAR(255) NOT NULL,
	role VARCHAR(20),
	phone VARCHAR(20),
	created_at DATETIME,
	CONSTRAINT pk_users PRIMARY KEY (id),
	CONSTRAINT ck_users_ck_users_role_valid CHECK (role IN ('farmer', 'developer', 'overseer', 'admin'))
);
CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_id ON users (id);
CREATE INDEX ix_users_role ON users (role);
CREATE INDEX ix_farms_user_id ON farms (user_id);
CREATE INDEX ix_fields_farm_id ON fields (farm_id);
CREATE INDEX ix_fields_crop_id ON fields (crop_id);
