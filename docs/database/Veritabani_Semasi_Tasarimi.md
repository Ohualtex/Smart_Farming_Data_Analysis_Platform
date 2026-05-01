SFDAP Veritabanı Şeması Tasarımı — Detaylı Plan
Akıllı Tarım Veri Analizi Platformu (SFDAP) için kapsamlı bir ilişkisel veritabanı şeması. Toprak nem verileri, mineral analizleri, IoT sensörler, hava durumu, bitki sağlığı, sulama, gübreleme ve hastalık tahmini modüllerini destekler.

1. Kullanıcı & Çiftlik Yönetimi
Tablo	Açıklama	Önemli Kolonlar
users	Çiftçi/admin hesapları	id, name, email, password_hash, role, phone, created_at
farms	Çiftlik tanımları	id, user_id (FK), name, location_lat, location_lng, area_hectares, city, region
fields	Tarla/parseller	id, farm_id (FK), name, area_hectares, soil_type, elevation_m, geometry_polygon
crop_types	Ekin türleri kataloğu	id, name, scientific_name, optimal_ph_min/max, optimal_temp_min/max, water_need_mm_per_day, growth_duration_days
field_crops	Tarladaki aktif ekinler	id, field_id (FK), crop_type_id (FK), planting_date, expected_harvest_date, status
2. Toprak Sensörleri & Nem Verileri (Detaylı)
IMPORTANT

Bu modül toprak nemini, sıcaklığını ve iletkenliğini zaman serisi olarak takip eder. Her sensör okuması depth_cm ile hangi derinlikten ölçüm alındığını kaydeder.

Tablo	Açıklama	Önemli Kolonlar
sensor_types	Sensör türleri kataloğu	id, name, manufacturer, measurement_unit, category (nem/mineral/sıcaklık/pH)
sensors	Sahaya yerleştirilmiş sensörler	id, field_id (FK), sensor_type_id (FK), serial_number, installation_date, depth_cm, lat, lng, status
soil_moisture_readings	Toprak nem ölçümleri	id, sensor_id (FK), field_id (FK), reading_timestamp, moisture_percent (%), depth_cm, soil_temperature_c, electrical_conductivity_ds_m (dS/m)
soil_moisture_thresholds	Ekin bazlı nem eşikleri	id, crop_type_id (FK), growth_stage, min_moisture_percent, max_moisture_percent, critical_low_percent
Detay: soil_moisture_readings tablosu yüksek frekanslı zaman serisi verisi içerir (ör. her 15 dk). depth_cm ile kök bölgesi nemi izlenir. electrical_conductivity_ds_m toprak tuzluluğunu ölçer.

3. Toprak Mineral & Besin Analizi (Yeni Modül)
IMPORTANT

Topraktaki makro/mikro besinlerin ve minerallerin analizini ayrıntılı olarak takip eden yeni tablolar. Bu veriler gübreleme önerilerinin temelini oluşturur.

Tablo	Açıklama	Önemli Kolonlar
soil_analysis_samples	Alınan toprak numuneleri	id, field_id (FK), sample_date, sample_depth_cm, sampled_by (FK→users), lab_name, lat, lng, notes
soil_mineral_results	Mineral analiz sonuçları	id, sample_id (FK), makro: nitrogen_ppm (Azot), phosphorus_ppm (Fosfor), potassium_ppm (Potasyum), calcium_ppm (Kalsiyum), magnesium_ppm (Magnezyum), sulfur_ppm (Kükürt), mikro: iron_ppm (Demir), zinc_ppm (Çinko), manganese_ppm (Mangan), copper_ppm (Bakır), boron_ppm (Bor), molybdenum_ppm (Molibden)
soil_ph_ec_readings	pH ve EC ölçümleri	id, sample_id (FK), ph_value, ec_value_ds_m, organic_matter_percent, cec_meq_100g (Katyon Değişim Kapasitesi), lime_percent
mineral_optimal_ranges	Ekin bazlı ideal mineral aralıkları	id, crop_type_id (FK), growth_stage, mineral_name, min_ppm, max_ppm, unit
soil_texture_analysis	Toprak bünyesi	id, sample_id (FK), sand_percent, silt_percent, clay_percent, texture_class (kumlu, killi, tınlı vb.), water_holding_capacity_mm, bulk_density_g_cm3
Detay: soil_mineral_results NPK (Azot-Fosfor-Potasyum) + 9 mikro besin elementini kapsar. soil_texture_analysis tablosu toprak bünyesini (kum/silt/kil oranları) ve su tutma kapasitesini saklar — bu sulama optimizasyonu için kritiktir.

4. Hava Durumu Verileri
Tablo	Açıklama	Önemli Kolonlar
weather_stations	Meteoroloji istasyonları	id, farm_id (FK), station_name, lat, lng, data_source (API/yerel)
weather_data	Anlık/saatlik hava verisi	id, station_id (FK), recorded_at, temperature_c, humidity_percent, precipitation_mm, wind_speed_kmh, wind_direction, solar_radiation_w_m2, uv_index, atmospheric_pressure_hpa, evapotranspiration_mm
weather_forecasts	Hava tahmini (7 gün)	id, station_id (FK), forecast_date, temp_min_c, temp_max_c, precipitation_probability, precipitation_expected_mm
5. Bitki Sağlığı & Hastalık Tespiti
Tablo	Açıklama	Önemli Kolonlar
disease_types	Hastalık/zararlı kataloğu	id, name, category (fungal/bakteriyel/viral/zararlı), description, treatment_recommendation
plant_health_images	Yüklenen bitki görselleri	id, field_crop_id (FK), image_url, captured_at, lat, lng, uploaded_by (FK)
disease_detections	ML model tespitleri	id, image_id (FK), disease_type_id (FK), confidence_score, severity (hafif/orta/şiddetli), detected_at, model_id (FK)
6. Sulama Optimizasyonu
Tablo	Açıklama	Önemli Kolonlar
irrigation_systems	Sulama sistemleri	id, field_id (FK), type (damla/yağmurlama/pivot), flow_rate_lph, efficiency_percent
irrigation_schedules	Planlanan sulamalar	id, field_id (FK), system_id (FK), scheduled_date, start_time, duration_min, water_amount_liters, source (model/manuel), status
irrigation_logs	Gerçekleşen sulamalar	id, schedule_id (FK), actual_start, actual_end, actual_water_liters, pre_moisture_pct, post_moisture_pct
7. Gübreleme Önerileri
Tablo	Açıklama	Önemli Kolonlar
fertilizer_types	Gübre kataloğu	id, name, n_percent, p_percent, k_percent, type (organik/kimyasal), form (granül/sıvı/toz)
fertilization_recommendations	Model önerileri	id, field_crop_id (FK), soil_analysis_id (FK), fertilizer_type_id (FK), recommended_amount_kg_ha, application_method, recommended_date, reasoning_json, model_id (FK)
fertilization_logs	Uygulanan gübrelemeler	id, recommendation_id (FK), applied_date, actual_amount_kg_ha, applied_by (FK), notes
8. ML Modelleri & Tahminler
Tablo	Açıklama	Önemli Kolonlar
ml_models	Eğitilmiş modeller	id, name, version, type (tahmin/sınıflandırma/görüntü), framework (TensorFlow/Keras), accuracy, trained_at, model_file_path
model_predictions	Model çıktıları	id, model_id (FK), field_id (FK), prediction_type, prediction_value_json, confidence_score, created_at
9. Raporlama & Uyarılar
Tablo	Açıklama	Önemli Kolonlar
reports	Periyodik raporlar	id, farm_id (FK), report_type, period_start, period_end, generated_at, file_url
alert_rules	Uyarı kuralları	id, farm_id (FK), metric, condition, threshold_value, severity, is_active
alerts	Tetiklenen uyarılar	id, rule_id (FK), field_id (FK), triggered_at, message, is_read, resolved_at
Tablo İlişkileri (ER Özet)
sahip
icerir
kurulu
ekili
analiz
sonuc
olcum
bunye
okuma
ideal_aralik
nem_esik
istasyon
veri
goruntu
tespit
sistem
plan
oneri
rapor
kural
users
farms
fields
sensors
field_crops
soil_analysis_samples
soil_mineral_results
soil_ph_ec_readings
soil_texture_analysis
soil_moisture_readings
crop_types
mineral_optimal_ranges
soil_moisture_thresholds
weather_stations
weather_data
plant_health_images
disease_detections
irrigation_systems
irrigation_schedules
fertilization_recommendations
reports
alert_rules
Teslim Edilecek Dosyalar
Dosya	Açıklama
database/sfdap_schema.sql	Tüm CREATE TABLE, indeksler, constraint'ler, örnek seed verileri
database/schema_documentation.md	ER diyagramı, tablo açıklamaları, ilişki detayları
Verification Plan
Manual Verification
SQL söz dizimi doğruluğu
FK ilişki tutarlılığı
ER diyagramının tüm tabloları yansıtması
