"""
Hava Durumu Servisi Testleri
==============================
WeatherService sınıfının veri temizleme, dönüştürme
ve enterpolasyon fonksiyonları test edilir.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.weather_service import WeatherService


@pytest.fixture
def service():
    return WeatherService()


# ───── VERİ TEMİZLEME TESTLERİ ───────────────────────────────────────────────
class TestCleanWeatherData:
    def test_valid_data_stays_unchanged(self, service):
        """Geçerli veri temizleme sonrası aynı kalmalı."""
        data = {
            "temperature_c": 25.0,
            "humidity_percent": 60.0,
            "precipitation_mm": 5.0,
            "wind_speed_kmh": 15.0,
            "solar_radiation": 800.0,
            "uv_index": 6.0,
        }
        cleaned = service.clean_weather_data(data)
        assert cleaned["temperature_c"] == 25.0
        assert cleaned["humidity_percent"] == 60.0

    def test_negative_precipitation_clipped_to_zero(self, service):
        """Negatif yağış sıfıra düzeltilmeli."""
        data = {"precipitation_mm": -5.0}
        cleaned = service.clean_weather_data(data)
        assert cleaned["precipitation_mm"] == 0.0

    def test_humidity_over_100_clipped(self, service):
        """100'ün üstünde nem değeri 100'e düşürülmeli."""
        data = {"humidity_percent": 120.0}
        cleaned = service.clean_weather_data(data)
        assert cleaned["humidity_percent"] == 100.0

    def test_extreme_temperature_clipped(self, service):
        """Aşırı sıcaklık değerleri sınırlanmalı."""
        data = {"temperature_c": 75.0}
        cleaned = service.clean_weather_data(data)
        assert cleaned["temperature_c"] == 60.0

    def test_negative_wind_speed_clipped(self, service):
        """Negatif rüzgar hızı sıfıra düzeltilmeli."""
        data = {"wind_speed_kmh": -10.0}
        cleaned = service.clean_weather_data(data)
        assert cleaned["wind_speed_kmh"] == 0.0

    def test_none_values_preserved(self, service):
        """None değerler korunmalı (temizleme işlemi yapılmamalı)."""
        data = {"temperature_c": None, "humidity_percent": None}
        cleaned = service.clean_weather_data(data)
        assert cleaned["temperature_c"] is None
        assert cleaned["humidity_percent"] is None


# ───── EKSİK VERİ DOLDURMA TESTLERİ ──────────────────────────────────────────
class TestFillMissingFields:
    def test_fill_none_fields(self, service):
        """None alanlar varsayılan değerlerle doldurulmalı."""
        data = {"temperature_c": None, "humidity_percent": None}
        filled = service.fill_missing_fields(data)
        assert filled["temperature_c"] == 20.0
        assert filled["humidity_percent"] == 50.0

    def test_existing_values_not_overwritten(self, service):
        """Zaten dolu olan alanlar üzerine yazılmamalı."""
        data = {"temperature_c": 30.0, "precipitation_mm": 10.0}
        filled = service.fill_missing_fields(data)
        assert filled["temperature_c"] == 30.0
        assert filled["precipitation_mm"] == 10.0

    def test_all_missing_fields_filled(self, service):
        """Tüm eksik alanlar doldurulmalı."""
        data = {}
        filled = service.fill_missing_fields(data)
        assert filled["temperature_c"] is not None
        assert filled["humidity_percent"] is not None
        assert filled["precipitation_mm"] is not None
        assert filled["wind_speed_kmh"] is not None


# ───── ENTERPOLASYON TESTLERİ ─────────────────────────────────────────────────
class TestInterpolateMissingData:
    def test_interpolate_fills_gaps(self, service):
        """Ortadaki eksik değer enterpolasyonla doldurulmalı."""
        records = [
            {"temperature_c": 20.0},
            {"temperature_c": None},
            {"temperature_c": 30.0},
        ]
        result = service.interpolate_missing_data(records, "temperature_c")
        assert result[1]["temperature_c"] == 25.0  # Lineer enterpolasyon

    def test_interpolate_empty_list(self, service):
        """Boş liste boş dönmeli."""
        result = service.interpolate_missing_data([], "temperature_c")
        assert result == []

    def test_interpolate_no_missing(self, service):
        """Eksik veri yoksa hiçbir şey değişmemeli."""
        records = [
            {"temperature_c": 20.0},
            {"temperature_c": 25.0},
            {"temperature_c": 30.0},
        ]
        result = service.interpolate_missing_data(records, "temperature_c")
        assert result[0]["temperature_c"] == 20.0
        assert result[1]["temperature_c"] == 25.0
        assert result[2]["temperature_c"] == 30.0


# ───── API DÖNÜŞTÜRME TESTLERİ ───────────────────────────────────────────────
class TestTransformApiResponse:
    def test_transform_basic_response(self, service):
        """OpenWeatherMap formatı platform formatına dönüşmeli."""
        raw = {
            "main": {"temp": 22.5, "humidity": 65},
            "wind": {"speed": 5.0},
            "rain": {"1h": 2.3},
            "clouds": {"all": 40},
        }
        result = service._transform_api_response(raw)
        assert result["temperature_c"] == 22.5
        assert result["humidity_percent"] == 65
        assert result["precipitation_mm"] == 2.3
        assert result["wind_speed_kmh"] == 18.0  # 5 m/s * 3.6

    def test_transform_missing_rain(self, service):
        """Yağmur verisi yoksa 0.0 olmalı."""
        raw = {
            "main": {"temp": 20.0, "humidity": 50},
            "wind": {"speed": 3.0},
            "rain": {},
            "clouds": {"all": 0},
        }
        result = service._transform_api_response(raw)
        assert result["precipitation_mm"] == 0.0

    def test_solar_radiation_estimation(self, service):
        """Güneş radyasyonu bulut oranına göre hesaplanmalı."""
        # Temiz gökyüzü
        clear = service._estimate_solar_radiation(0)
        assert clear == 1000.0

        # Tam bulutlu
        cloudy = service._estimate_solar_radiation(100)
        assert cloudy == 200.0


# ───── DEMO VERİ TESTLERİ ────────────────────────────────────────────────────
class TestDemoData:
    def test_demo_weather_has_all_fields(self, service):
        """Demo veri tüm gerekli alanları içermeli."""
        demo = service._generate_demo_weather()
        assert "temperature_c" in demo
        assert "humidity_percent" in demo
        assert "precipitation_mm" in demo
        assert "wind_speed_kmh" in demo
        assert "recorded_at" in demo

    def test_demo_values_in_range(self, service):
        """Demo değerler gerçekçi aralıklarda olmalı."""
        demo = service._generate_demo_weather()
        assert 10 <= demo["temperature_c"] <= 35
        assert 30 <= demo["humidity_percent"] <= 90
        assert 0 <= demo["precipitation_mm"] <= 15


# ───── WEATHER ROUTER TESTLERİ ────────────────────────────────────────────────
class TestWeatherCleanEndpoint:
    def test_clean_endpoint_returns_three_keys(self, client):
        """Clean endpoint original, cleaned, filled döndürmeli."""
        data = {"temperature_c": 25.0, "humidity_percent": -5.0}
        response = client.post("/api/weather/clean", json=data)
        assert response.status_code == 200
        body = response.json()
        assert "original" in body
        assert "cleaned" in body
        assert "filled" in body

    def test_clean_endpoint_fixes_invalid(self, client):
        """Geçersiz nem değeri düzeltilmeli."""
        data = {"humidity_percent": -10.0}
        response = client.post("/api/weather/clean", json=data)
        body = response.json()
        assert body["cleaned"]["humidity_percent"] == 0.0


class TestWeatherStatsEndpoint:
    def test_stats_empty_farm(self, client):
        """Veri olmayan çiftlik için bilgi mesajı dönmeli.

        RBAC sonrası: olmayan farm_id artık 404 — testin amacı "weather
        verisi olmayan ama mevcut farm" senaryosu olduğu için default
        farm (id=1, conftest seed) kullanılır. Hiç weather kaydı eklenmediği
        için record_count=0 beklenir.
        """
        response = client.get("/api/weather/stats/1?days=7")
        assert response.status_code == 200
        body = response.json()
        assert body["record_count"] == 0

    def test_stats_with_data(self, client):
        """Veri olan çiftlik için istatistikler dönmeli."""
        # Önce veri ekle
        for temp in [20.0, 25.0, 30.0]:
            client.post(
                "/api/weather/",
                json={
                    "farm_id": 1,
                    "temperature_c": temp,
                    "humidity_percent": 55.0,
                    "precipitation_mm": 2.0,
                },
            )
        response = client.get("/api/weather/stats/1?days=7")
        body = response.json()
        assert body["record_count"] == 3
        assert body["temperature"]["avg"] == 25.0


# ───── DIŞ API ENTEGRASYONU (HTTPX MOCK) ─────────────────────────────────────


class TestFetchCurrentWeather:
    """`fetch_current_weather` async metodu — API key yok ve var path'leri."""

    def test_returns_demo_when_no_api_key(self, service, monkeypatch):
        """API key boşsa httpx çağrılmadan demo veri dönmeli."""
        service.api_key = None
        result = asyncio.run(service.fetch_current_weather(40.0, 33.0))
        # Demo veri tüm alanları içerir
        assert "temperature_c" in result
        assert "humidity_percent" in result
        assert "recorded_at" in result

    def test_calls_httpx_when_api_key_set(self, service, monkeypatch):
        """API key set edilmişse httpx.AsyncClient.get çağrılmalı."""
        service.api_key = "test-key"

        # httpx.AsyncClient'i mock'la
        fake_response = MagicMock()
        fake_response.json.return_value = {
            "main": {"temp": 18.5, "humidity": 70},
            "wind": {"speed": 4.0},
            "rain": {"1h": 1.2},
            "clouds": {"all": 30},
        }
        fake_response.raise_for_status = MagicMock()

        fake_client = MagicMock()
        fake_client.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client.__aexit__ = AsyncMock(return_value=None)
        fake_client.get = AsyncMock(return_value=fake_response)

        monkeypatch.setattr(
            "app.services.weather_service.httpx.AsyncClient",
            lambda **kwargs: fake_client,
        )

        result = asyncio.run(service.fetch_current_weather(40.0, 33.0))

        assert result["temperature_c"] == 18.5
        assert result["humidity_percent"] == 70
        assert result["precipitation_mm"] == 1.2
        fake_client.get.assert_called_once()


class TestFetchForecast:
    """`fetch_forecast` async metodu — demo ve gerçek API path'leri."""

    def test_returns_demo_list_when_no_api_key(self, service):
        """API key boşsa N×8 demo kayıtlık liste dönmeli."""
        service.api_key = None
        result = asyncio.run(service.fetch_forecast(40.0, 33.0, days=2))
        # 2 gün × 8 = 16 kayıt
        assert len(result) == 16
        assert all("temperature_c" in r for r in result)

    def test_transforms_api_list_when_api_key_set(self, service, monkeypatch):
        """API key varsa list[dict] döndürmeli — her item _transform'dan geçer."""
        service.api_key = "test-key"
        fake_response = MagicMock()
        fake_response.json.return_value = {
            "list": [
                {"main": {"temp": 22.0, "humidity": 60}, "wind": {"speed": 3.0}, "rain": {}, "clouds": {"all": 20}},
                {
                    "main": {"temp": 24.0, "humidity": 55},
                    "wind": {"speed": 4.0},
                    "rain": {"3h": 0.5},
                    "clouds": {"all": 60},
                },
            ]
        }
        fake_response.raise_for_status = MagicMock()

        fake_client = MagicMock()
        fake_client.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client.__aexit__ = AsyncMock(return_value=None)
        fake_client.get = AsyncMock(return_value=fake_response)

        monkeypatch.setattr(
            "app.services.weather_service.httpx.AsyncClient",
            lambda **kwargs: fake_client,
        )

        result = asyncio.run(service.fetch_forecast(40.0, 33.0))
        assert len(result) == 2
        assert result[0]["temperature_c"] == 22.0
        assert result[1]["precipitation_mm"] == 0.5


class TestSaveWeatherRecord:
    """`save_weather_record` veri temizleme + DB persistence akışı."""

    def test_persists_cleaned_filled_record(self, service, db, client):
        """Temizleme + doldurma + DB INSERT akışı tutarlı çalışmalı."""
        # client fixture seed çalıştırarak farm_id=1'i hazırlar
        # Ham veri eksik alan + sınır ihlali içeriyor
        raw = {
            "temperature_c": 200,  # sınır ihlali → 60'a clip
            "humidity_percent": -5,  # negatif → 0
            "precipitation_mm": None,  # None → fill default
        }
        record = service.save_weather_record(db, farm_id=1, data=raw)

        assert record.id is not None
        assert record.temperature_c == 60.0  # clipped
        assert record.humidity_percent == 0.0  # clipped from negative
        assert record.precipitation_mm == 0.0  # filled default
