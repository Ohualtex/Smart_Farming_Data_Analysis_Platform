import pytest
import time
from fastapi.testclient import TestClient
from app import app  # Senin yazdığın ana uygulama dosyası

client = TestClient(app)

# --- KONFİGÜRASYON ---
VALID_API_KEY = "akilli_tarim_gizli_anahtar_2026"
INVALID_API_KEY = "yanlis_anahtar_123"

# --- 1. GÜVENLİK VE YETKİLENDİRME TESTLERİ ---

def test_security_missing_header():
    """Header içinde hiç API Key gönderilmezse sistem 403 vermeli."""
    response = client.get("/api/v1/soil-data")
    assert response.status_code == 403
    assert "detail" in response.json()

def test_security_invalid_key():
    """Yanlış API Key gönderildiğinde erişim reddedilmeli."""
    headers = {"X-API-Key": INVALID_API_KEY}
    response = client.get("/api/v1/soil-data", headers=headers)
    assert response.status_code == 403
    assert "Hata" in response.json()["detail"]

# --- 2. VERİ DOĞRULAMA (VALIDATION) TESTLERİ ---

def test_get_soil_data_structure():
    """Başarılı girişte verilerin doğru şemada gelip gelmediği kontrolü."""
    headers = {"X-API-Key": VALID_API_KEY}
    response = client.get("/api/v1/soil-data", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)  # Veri bir liste olmalı
    
    # Listedeki ilk verinin içeriğini kontrol et
    if len(data) > 0:
        first_item = data[0]
        assert "sensor_id" in first_item
        assert "moisture" in first_item
        assert isinstance(first_item["moisture"], (int, float))

def test_weather_data_endpoint():
    """Hava durumu endpoint'inin doğruluğu."""
    headers = {"X-API-Key": VALID_API_KEY}
    response = client.get("/api/v1/weather-data", headers=headers)
    assert response.status_code == 200
    assert "status" in response.json()

# --- 3. PERFORMANS TESTLERİ ---

def test_response_latency():
    """API yanıt süresinin 100ms altında olup olmadığının ölçümü."""
    headers = {"X-API-Key": VALID_API_KEY}
    start_time = time.time()
    client.get("/api/v1/soil-data", headers=headers)
    end_time = time.time()
    
    duration = (end_time - start_time) * 1000  # milisaniyeye çevir
    assert duration < 100  # 100ms sınırı
