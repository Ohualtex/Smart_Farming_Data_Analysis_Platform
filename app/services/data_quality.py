"""
Veri Kalitesi & Temizleme Yardımcıları
========================================
Sensör okumaları ve hava durumu verisi gibi zaman serisi verilerinde
aykırı değer tespiti, eksik veri doldurma ve sınır kontrolü için
yeniden kullanılabilir helper'lar.

Emirhan Günay — Cycle 6 Görevi (shiftSession): Veri Temizleme ve
Dönüştürme İşlemlerini İyileştirme

Skeleton: temel statistik tabanlı outlier ve missing-value işleyiciler.
Genişletme önerileri:
- Z-score ile çok değişkenli outlier tespiti
- ARIMA / Kalman tabanlı interpolasyon
- Sensör bazlı aralık (kalibrasyon) tabanlı validasyon
- Time series rolling window stats
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence


def detect_outliers_iqr(values: Sequence[float], factor: float = 1.5) -> list[int]:
    """
    Tukey'in IQR yöntemi ile aykırı değer indekslerini döndürür.

    Q1 - factor*IQR  altı veya  Q3 + factor*IQR  üstündekiler outlier.

    Args:
        values: sayısal değer dizisi (None'lar tolerans dışı, önceden filtrele)
        factor: IQR çarpanı (1.5 standart, 3.0 daha tutucu)

    Returns:
        outlier sayılan indekslerin listesi
    """
    if len(values) < 4:
        return []
    q1 = statistics.quantiles(values, n=4)[0]
    q3 = statistics.quantiles(values, n=4)[2]
    iqr = q3 - q1
    lower = q1 - factor * iqr
    upper = q3 + factor * iqr
    return [i for i, v in enumerate(values) if v < lower or v > upper]


def fill_missing_linear(values: list[float | None]) -> list[float]:
    """
    None/NaN'ları doğrusal interpolasyon ile doldurur.

    Baş ve sondaki None'lar en yakın geçerli değerle doldurulur.
    Dizide hiç geçerli değer yoksa boş liste döndürülür.

    Args:
        values: None içerebilen liste (örn: [1.0, None, 3.0, None, 5.0])

    Returns:
        Tüm None'ları doldurulmuş float list (örn: [1.0, 2.0, 3.0, 4.0, 5.0])
    """
    valid = [(i, v) for i, v in enumerate(values) if v is not None]
    if not valid:
        return []

    out: list[float] = [0.0] * len(values)
    for i, v in enumerate(values):
        if v is not None:
            out[i] = v
            continue
        # En yakın önceki ve sonraki geçerli değeri bul
        prev = next((p for p in reversed(valid) if p[0] < i), None)
        nxt = next((p for p in valid if p[0] > i), None)
        if prev and nxt:
            slope = (nxt[1] - prev[1]) / (nxt[0] - prev[0])
            out[i] = prev[1] + slope * (i - prev[0])
        elif prev:
            out[i] = prev[1]
        elif nxt:
            out[i] = nxt[1]
    return out


def clip_to_range(value: float, low: float, high: float) -> float:
    """Değeri [low, high] aralığına kıs (kalibrasyon sınırları için)."""
    return max(low, min(high, value))


def validate_sensor_reading(
    reading: dict,
    bounds: dict[str, tuple[float, float]] | None = None,
) -> tuple[bool, list[str]]:
    """
    Sensör okumasının fiziksel sınırlar içinde olup olmadığını doğrular.

    Args:
        reading: {"moisture_percent": 45.0, "soil_temperature_c": 22.0, ...}
        bounds: alan adı → (min, max). None verilirse default fiziksel limitler.

    Returns:
        (geçerli_mi, hata_mesajları)
    """
    default_bounds = {
        "moisture_percent": (0.0, 100.0),
        "soil_temperature_c": (-20.0, 70.0),
        "electrical_conductivity": (0.0, 20.0),
        "depth_cm": (0.0, 200.0),
    }
    bounds = bounds or default_bounds
    errors: list[str] = []
    for field, (low, high) in bounds.items():
        value = reading.get(field)
        if value is None:
            continue
        if not low <= value <= high:
            errors.append(f"{field}={value} sınır dışı [{low}, {high}]")
    return len(errors) == 0, errors
