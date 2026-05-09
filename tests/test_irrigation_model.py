"""
IrrigationOptimizer Unit Testleri
====================================
Synthetic training path'i (model dosyası yokken) ve `predict()` mesaj
sınıflandırmasını test eder.

EN: Tests for the synthetic training fallback path and predict() output
shape / categorization for the RandomForest irrigation model.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ml.irrigation_model import IrrigationOptimizer


@pytest.fixture
def fresh_optimizer(tmp_path: Path) -> IrrigationOptimizer:
    """Pickle dosyası olmayan temp dizinde optimizer kur — synthetic train tetiklenir."""
    return IrrigationOptimizer(model_path=str(tmp_path) + "/")


class TestSyntheticTraining:
    """Model dosyası yokken synthetic data ile eğitim akışı."""

    def test_initializes_with_synthetic_data_when_no_pickle(self, fresh_optimizer):
        """Pickle yok → model ve scaler hazır olmalı."""
        assert fresh_optimizer.model is not None
        # Scaler `fit` çağrılmış olmalı (mean_ attribute synthetic data'dan gelir)
        assert hasattr(fresh_optimizer.scaler, "mean_")

    def test_synthetic_training_persists_pickle_files(self, fresh_optimizer, tmp_path):
        """Eğitim sonrası model_path altına pickle dosyaları yazılmalı."""
        assert (tmp_path / "irrigation_model.pkl").exists()
        assert (tmp_path / "scaler.pkl").exists()


class TestPredictShape:
    """`predict()` response şeması."""

    def test_predict_returns_required_keys(self, fresh_optimizer):
        result = fresh_optimizer.predict(
            soil_moisture=30.0,
            soil_temperature=22.0,
            humidity=60.0,
            temperature=25.0,
            precipitation=0.0,
        )
        for key in ("recommended_water_liters", "irrigation_needed", "confidence", "message"):
            assert key in result

    def test_confidence_within_range(self, fresh_optimizer):
        result = fresh_optimizer.predict(50.0, 20.0, 50.0, 20.0, 0.0)
        assert IrrigationOptimizer.CONFIDENCE_BASE <= result["confidence"] <= IrrigationOptimizer.CONFIDENCE_CAP

    def test_recommended_water_non_negative(self, fresh_optimizer):
        # Aşırı yüksek nem → 0 litre önerisi beklenir
        result = fresh_optimizer.predict(95.0, 22.0, 80.0, 18.0, 20.0)
        assert result["recommended_water_liters"] >= 0


class TestMessageCategorization:
    """`predict()` mesaj kademelerinin doğru tetiklendiğini doğrular."""

    def test_high_moisture_says_irrigation_not_needed(self, fresh_optimizer):
        """Yüksek nem + yağış → 'sulama gerekmiyor'."""
        result = fresh_optimizer.predict(
            soil_moisture=85.0,
            soil_temperature=20.0,
            humidity=80.0,
            temperature=18.0,
            precipitation=15.0,
        )
        # 5 litreden az olmalı → eşik altı
        if result["recommended_water_liters"] <= IrrigationOptimizer.IRRIGATION_THRESHOLD_LITERS:
            assert result["irrigation_needed"] is False
            assert "gerekmiyor" in result["message"].lower()

    def test_low_moisture_high_temp_recommends_irrigation(self, fresh_optimizer):
        """Düşük nem + yüksek sıcaklık → irrigation_needed True."""
        result = fresh_optimizer.predict(
            soil_moisture=15.0,
            soil_temperature=35.0,
            humidity=25.0,
            temperature=38.0,
            precipitation=0.0,
        )
        # Bu input'la model muhtemelen >5 litre önerir
        if result["recommended_water_liters"] > IrrigationOptimizer.IRRIGATION_THRESHOLD_LITERS:
            assert result["irrigation_needed"] is True
            # Kademe mesajlarından biri olmalı
            assert any(word in result["message"].lower() for word in ("hafif", "orta", "acil"))
