"""
Hava Durumu Veri Servisi
========================
OpenWeatherMap API'den veri çekme, temizleme, dönüştürme ve
eksik veri enterpolasyonu işlemleri.

Ayşe Eslem Çekici — Cycle 4 Görevi
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.config import settings
from app.models.models import WeatherData


class WeatherService:
    """
    Hava durumu verilerini dış API'den çekip temizleyen,
    dönüştüren ve veritabanına kaydeden servis sınıfı.
    """

    OPENWEATHERMAP_BASE = "https://api.openweathermap.org/data/2.5"

    def __init__(self):
        self.api_key = settings.OPENWEATHERMAP_API_KEY

    # ─── DIŞ API'DEN VERİ ÇEKME ─────────────────────────────────────────

    async def fetch_current_weather(self, lat: float, lon: float) -> dict:
        """
        OpenWeatherMap API'den anlık hava durumu verisini çeker.
        API key yoksa demo veri döndürür.
        """
        if not self.api_key:
            return self._generate_demo_weather()

        url = f"{self.OPENWEATHERMAP_BASE}/weather"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": "metric",
            "lang": "tr",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return self._transform_api_response(response.json())

    async def fetch_forecast(self, lat: float, lon: float, days: int = 5) -> list[dict]:
        """
        OpenWeatherMap API'den 5 günlük tahmin verisini çeker.
        API key yoksa demo veri döndürür.
        """
        if not self.api_key:
            return [self._generate_demo_weather() for _ in range(days * 8)]

        url = f"{self.OPENWEATHERMAP_BASE}/forecast"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": "metric",
            "lang": "tr",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return [self._transform_api_response(item) for item in data.get("list", [])]

    # ─── VERİ DÖNÜŞTÜRME ────────────────────────────────────────────────

    def _transform_api_response(self, raw: dict) -> dict:
        """
        OpenWeatherMap ham verisini platformun veri modeline dönüştürür.
        Sıcaklık, nem, yağış, rüzgar hızı ve güneş radyasyonu bilgilerini çıkarır.
        """
        main = raw.get("main", {})
        wind = raw.get("wind", {})
        rain = raw.get("rain", {})
        clouds = raw.get("clouds", {})

        return {
            "temperature_c": main.get("temp"),
            "humidity_percent": main.get("humidity"),
            "precipitation_mm": rain.get("1h", rain.get("3h", 0.0)),
            "wind_speed_kmh": round((wind.get("speed", 0) * 3.6), 2),  # m/s → km/h
            "solar_radiation": self._estimate_solar_radiation(clouds.get("all", 50)),
            "uv_index": None,  # Ayrı API çağrısı gerekir
            "recorded_at": datetime.now(timezone.utc),
        }

    def _estimate_solar_radiation(self, cloud_cover_percent: float) -> float:
        """
        Bulut oranından tahmini güneş radyasyonu hesaplar (W/m²).
        Temiz gökyüzü ~ 1000 W/m², tam bulutlu ~ 200 W/m²
        """
        max_radiation = 1000.0
        return round(max_radiation * (1 - cloud_cover_percent / 100 * 0.8), 1)

    def _generate_demo_weather(self) -> dict:
        """API key yokken test verisi üretir."""
        rng = np.random.default_rng()
        return {
            "temperature_c": round(rng.uniform(10, 35), 1),
            "humidity_percent": round(rng.uniform(30, 90), 1),
            "precipitation_mm": round(rng.uniform(0, 15), 1),
            "wind_speed_kmh": round(rng.uniform(0, 40), 1),
            "solar_radiation": round(rng.uniform(200, 900), 1),
            "uv_index": round(rng.uniform(1, 10), 1),
            "recorded_at": datetime.now(timezone.utc),
        }

    # ─── VERİ TEMİZLEME ─────────────────────────────────────────────────

    def clean_weather_data(self, data: dict) -> dict:
        """
        Hava durumu verisini temizler:
        - None/NaN değerleri tespit eder
        - Fiziksel sınırların dışındaki aykırı değerleri düzeltir
        - Negatif yağış/nem gibi imkansız değerleri sıfırlar
        """
        cleaned = data.copy()

        # Sıcaklık: -50 ile +60 arası geçerli
        if cleaned.get("temperature_c") is not None:
            cleaned["temperature_c"] = float(np.clip(cleaned["temperature_c"], -50, 60))

        # Nem: 0-100 arası
        if cleaned.get("humidity_percent") is not None:
            cleaned["humidity_percent"] = float(np.clip(cleaned["humidity_percent"], 0, 100))

        # Yağış: 0 veya pozitif
        if cleaned.get("precipitation_mm") is not None:
            cleaned["precipitation_mm"] = max(0.0, float(cleaned["precipitation_mm"]))

        # Rüzgar hızı: 0 veya pozitif, max 250 km/h
        if cleaned.get("wind_speed_kmh") is not None:
            cleaned["wind_speed_kmh"] = float(np.clip(cleaned["wind_speed_kmh"], 0, 250))

        # Güneş radyasyonu: 0-1500 W/m²
        if cleaned.get("solar_radiation") is not None:
            cleaned["solar_radiation"] = float(np.clip(cleaned["solar_radiation"], 0, 1500))

        # UV indeksi: 0-15
        if cleaned.get("uv_index") is not None:
            cleaned["uv_index"] = float(np.clip(cleaned["uv_index"], 0, 15))

        return cleaned

    # ─── EKSİK VERİ ENTERPOLASYONU ──────────────────────────────────────

    def interpolate_missing_data(self, records: list[dict], column: str) -> list[dict]:
        """
        Eksik verileri lineer enterpolasyon ile doldurur.
        Pandas kullanarak NaN değerleri interpolasyon ile tamamlar.

        Args:
            records: Hava durumu kayıtları listesi
            column: Enterpolasyon yapılacak sütun adı

        Returns:
            Eksik verileri tamamlanmış kayıt listesi
        """
        if not records:
            return records

        df = pd.DataFrame(records)

        if column in df.columns:
            # Sayısal dönüşüm (hatalı string varsa NaN'e çevir)
            df[column] = pd.to_numeric(df[column], errors="coerce")

            # Lineer enterpolasyon
            df[column] = df[column].interpolate(method="linear", limit_direction="both")

            # Hala kalan NaN varsa sütun ortalaması ile doldur
            col_mean = df[column].mean()
            if pd.notna(col_mean):
                df[column] = df[column].fillna(col_mean)

        return df.to_dict("records")

    def fill_missing_fields(self, data: dict) -> dict:
        """
        Tek bir kayıttaki eksik alanları varsayılan değerlerle doldurur.
        """
        defaults = {
            "temperature_c": 20.0,
            "humidity_percent": 50.0,
            "precipitation_mm": 0.0,
            "wind_speed_kmh": 10.0,
            "solar_radiation": 500.0,
            "uv_index": 5.0,
        }

        filled = data.copy()
        for key, default_val in defaults.items():
            if filled.get(key) is None:
                filled[key] = default_val

        return filled

    # ─── VERİTABANI İŞLEMLERİ ───────────────────────────────────────────

    def save_weather_record(self, db: Session, farm_id: int, data: dict) -> WeatherData:
        """
        Temizlenmiş ve doldurulmuş hava verisi kaydını veritabanına kaydeder.
        """
        cleaned = self.clean_weather_data(data)
        filled = self.fill_missing_fields(cleaned)

        record = WeatherData(
            farm_id=farm_id,
            temperature_c=filled["temperature_c"],
            humidity_percent=filled["humidity_percent"],
            precipitation_mm=filled["precipitation_mm"],
            wind_speed_kmh=filled["wind_speed_kmh"],
            solar_radiation=filled.get("solar_radiation"),
            uv_index=filled.get("uv_index"),
            recorded_at=filled.get("recorded_at", datetime.now(timezone.utc)),
        )

        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def get_weather_stats(self, db: Session, farm_id: int, days: int = 7) -> dict:
        """
        Belirli bir çiftliğin son N günlük hava durumu istatistiklerini döndürür.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)

        records = (
            db.query(WeatherData).filter(WeatherData.farm_id == farm_id).filter(WeatherData.recorded_at >= since).all()
        )

        if not records:
            return {
                "farm_id": farm_id,
                "period_days": days,
                "record_count": 0,
                "message": "Bu dönem için veri bulunamadi",
            }

        temps = [r.temperature_c for r in records if r.temperature_c is not None]
        humidity = [r.humidity_percent for r in records if r.humidity_percent is not None]
        precip = [r.precipitation_mm for r in records if r.precipitation_mm is not None]

        return {
            "farm_id": farm_id,
            "period_days": days,
            "record_count": len(records),
            "temperature": {
                "avg": round(np.mean(temps), 1) if temps else None,
                "min": round(min(temps), 1) if temps else None,
                "max": round(max(temps), 1) if temps else None,
            },
            "humidity": {
                "avg": round(np.mean(humidity), 1) if humidity else None,
                "min": round(min(humidity), 1) if humidity else None,
                "max": round(max(humidity), 1) if humidity else None,
            },
            "precipitation": {
                "total_mm": round(sum(precip), 1) if precip else 0,
                "avg_per_day": round(sum(precip) / days, 1) if precip else 0,
                "rainy_days": sum(1 for p in precip if p > 0.5),
            },
        }


# Singleton instance
weather_service = WeatherService()
