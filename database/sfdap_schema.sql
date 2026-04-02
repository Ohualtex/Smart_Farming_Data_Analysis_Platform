-- =============================================
-- SFDAP - Akilli Tarim Veri Analizi Platformu
-- Veritabani Semasi (PostgreSQL / SQLite uyumlu)
-- Hazirlayan: Emirhan Gunay semasindan uyarlandi
-- =============================================

-- 1. Kullanici Yonetimi
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'farmer',
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Ciftlik Tanimlari
CREATE TABLE IF NOT EXISTS farms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name VARCHAR(150) NOT NULL,
    location_lat REAL,
    location_lng REAL,
    area_hectares REAL,
    city VARCHAR(100),
    region VARCHAR(100)
);

-- 3. Tarla / Parseller
CREATE TABLE IF NOT EXISTS fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    farm_id INTEGER NOT NULL REFERENCES farms(id),
    name VARCHAR(150) NOT NULL,
    area_hectares REAL,
    soil_type VARCHAR(50),
    elevation_m REAL
);

-- 4. Ekin Turleri
CREATE TABLE IF NOT EXISTS crop_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    scientific_name VARCHAR(150),
    optimal_ph_min REAL,
    optimal_ph_max REAL,
    optimal_temp_min REAL,
    optimal_temp_max REAL,
    water_need_mm_per_day REAL,
    growth_duration_days INTEGER
);

-- 5. Sensorler
CREATE TABLE IF NOT EXISTS sensors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    field_id INTEGER NOT NULL REFERENCES fields(id),
    sensor_type VARCHAR(50) NOT NULL,
    serial_number VARCHAR(100) UNIQUE,
    installation_date TIMESTAMP,
    depth_cm REAL,
    lat REAL,
    lng REAL,
    status VARCHAR(20) DEFAULT 'active'
);

-- 6. Toprak Nem Okumalari
CREATE TABLE IF NOT EXISTS soil_moisture_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_id INTEGER NOT NULL REFERENCES sensors(id),
    reading_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    moisture_percent REAL NOT NULL,
    depth_cm REAL,
    soil_temperature_c REAL,
    electrical_conductivity REAL
);

-- 7. Hava Durumu Verileri
CREATE TABLE IF NOT EXISTS weather_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    farm_id INTEGER REFERENCES farms(id),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    temperature_c REAL,
    humidity_percent REAL,
    precipitation_mm REAL,
    wind_speed_kmh REAL,
    solar_radiation REAL,
    uv_index REAL
);

-- 8. Sulama Planlari
CREATE TABLE IF NOT EXISTS irrigation_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    field_id INTEGER NOT NULL REFERENCES fields(id),
    scheduled_date TIMESTAMP NOT NULL,
    duration_min INTEGER,
    water_amount_liters REAL,
    source VARCHAR(20) DEFAULT 'model',
    status VARCHAR(20) DEFAULT 'pending'
);

-- 9. Bitki Sagligi Goruntuleri
CREATE TABLE IF NOT EXISTS plant_health_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    field_id INTEGER REFERENCES fields(id),
    image_url VARCHAR(500),
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    diagnosis VARCHAR(200),
    confidence_score REAL,
    severity VARCHAR(20)
);

-- Indeksler
CREATE INDEX IF NOT EXISTS idx_readings_sensor ON soil_moisture_readings(sensor_id);
CREATE INDEX IF NOT EXISTS idx_readings_time ON soil_moisture_readings(reading_timestamp);
CREATE INDEX IF NOT EXISTS idx_weather_farm ON weather_data(farm_id);
CREATE INDEX IF NOT EXISTS idx_weather_time ON weather_data(recorded_at);
