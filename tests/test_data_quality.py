"""
Data Quality Helper Tests
===========================
Covers outlier detection, missing-value imputation, and range-clipping
utilities in `app.services.data_quality`.

---

Veri kalitesi helper'ları (outlier, eksik veri, range clip) testleri.
"""

from __future__ import annotations

from app.services.data_quality import (
    clip_to_range,
    detect_outliers_iqr,
    fill_missing_linear,
    validate_sensor_reading,
)


class TestDetectOutliersIQR:
    def test_no_outliers_in_uniform_data(self):
        values = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0]
        assert detect_outliers_iqr(values) == []

    def test_detects_high_outlier(self):
        values = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 100.0]
        outliers = detect_outliers_iqr(values)
        assert 6 in outliers  # index of 100.0

    def test_detects_low_outlier(self):
        values = [-100.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
        outliers = detect_outliers_iqr(values)
        assert 0 in outliers

    def test_empty_input(self):
        assert detect_outliers_iqr([]) == []

    def test_too_few_values(self):
        # < 4 değerle çeyreklik hesaplanamaz
        assert detect_outliers_iqr([1.0, 2.0]) == []

    def test_factor_param_changes_strictness(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 25.0]
        # Daha geniş factor = daha az outlier
        strict = detect_outliers_iqr(values, factor=1.0)
        loose = detect_outliers_iqr(values, factor=3.0)
        assert len(loose) <= len(strict)


class TestFillMissingLinear:
    def test_no_missing_returns_same(self):
        assert fill_missing_linear([1.0, 2.0, 3.0]) == [1.0, 2.0, 3.0]

    def test_interpolate_middle(self):
        result = fill_missing_linear([1.0, None, 3.0])
        assert result == [1.0, 2.0, 3.0]

    def test_interpolate_multiple_gaps(self):
        result = fill_missing_linear([1.0, None, None, 4.0])
        assert result[0] == 1.0
        assert result[3] == 4.0
        # 1 + (3/3)*1 = 2, 1 + (3/3)*2 = 3
        assert abs(result[1] - 2.0) < 1e-9
        assert abs(result[2] - 3.0) < 1e-9

    def test_leading_none_uses_next(self):
        result = fill_missing_linear([None, None, 5.0, 6.0])
        assert result[0] == 5.0
        assert result[1] == 5.0

    def test_trailing_none_uses_prev(self):
        result = fill_missing_linear([1.0, 2.0, None, None])
        assert result[2] == 2.0
        assert result[3] == 2.0

    def test_all_none_returns_empty(self):
        assert fill_missing_linear([None, None, None]) == []


class TestClipToRange:
    def test_in_range(self):
        assert clip_to_range(5.0, 0.0, 10.0) == 5.0

    def test_above(self):
        assert clip_to_range(15.0, 0.0, 10.0) == 10.0

    def test_below(self):
        assert clip_to_range(-5.0, 0.0, 10.0) == 0.0


class TestValidateSensorReading:
    def test_valid_reading(self):
        reading = {
            "moisture_percent": 45.0,
            "soil_temperature_c": 22.0,
            "electrical_conductivity": 1.5,
        }
        ok, errors = validate_sensor_reading(reading)
        assert ok is True
        assert errors == []

    def test_invalid_moisture(self):
        reading = {"moisture_percent": 150.0}
        ok, errors = validate_sensor_reading(reading)
        assert ok is False
        assert len(errors) == 1
        assert "moisture_percent" in errors[0]

    def test_multiple_errors(self):
        reading = {
            "moisture_percent": -10.0,
            "soil_temperature_c": 200.0,
        }
        ok, errors = validate_sensor_reading(reading)
        assert ok is False
        assert len(errors) == 2

    def test_missing_fields_skipped(self):
        # Eksik alanlar hata sebebi değil
        reading = {"moisture_percent": 50.0}
        ok, errors = validate_sensor_reading(reading)
        assert ok is True

    def test_custom_bounds(self):
        reading = {"moisture_percent": 50.0}
        ok, errors = validate_sensor_reading(reading, bounds={"moisture_percent": (0.0, 30.0)})
        assert ok is False
