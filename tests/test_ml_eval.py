"""
ML Eval helper testleri
========================
Ayşe'nin Cycle 6 görevi için skeleton testler.
"""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeClassifier

from app.ml.eval import classification_metrics, cross_validate, regression_metrics


class TestRegressionMetrics:
    def test_perfect_prediction(self):
        y_true = np.array([1.0, 2.0, 3.0, 4.0])
        y_pred = np.array([1.0, 2.0, 3.0, 4.0])
        m = regression_metrics(y_true, y_pred)
        assert m["mae"] == 0.0
        assert m["mse"] == 0.0
        assert m["rmse"] == 0.0
        assert m["r2"] == 1.0

    def test_returns_all_keys(self):
        y_true = np.array([1.0, 2.0, 3.0])
        y_pred = np.array([1.1, 2.1, 2.9])
        m = regression_metrics(y_true, y_pred)
        assert set(m.keys()) == {"mae", "mse", "rmse", "r2"}
        assert all(isinstance(v, float) for v in m.values())

    def test_rmse_is_sqrt_mse(self):
        y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_pred = np.array([1.5, 1.5, 3.5, 3.5, 5.5])
        m = regression_metrics(y_true, y_pred)
        assert abs(m["rmse"] - m["mse"] ** 0.5) < 1e-9


class TestClassificationMetrics:
    def test_perfect_classification(self):
        y_true = np.array([0, 1, 1, 0, 1])
        y_pred = np.array([0, 1, 1, 0, 1])
        m = classification_metrics(y_true, y_pred)
        assert m["accuracy"] == 1.0
        assert m["precision"] == 1.0
        assert m["recall"] == 1.0
        assert m["f1"] == 1.0

    def test_returns_all_keys(self):
        y_true = np.array([0, 1, 1, 0])
        y_pred = np.array([0, 0, 1, 0])
        m = classification_metrics(y_true, y_pred)
        assert set(m.keys()) == {"accuracy", "precision", "recall", "f1"}

    def test_zero_division_safe(self):
        # Tüm tahminler 0, hiç pozitif yok — precision normalde NaN ama 0 dönmeli
        y_true = np.array([0, 0, 0, 0])
        y_pred = np.array([0, 0, 0, 0])
        m = classification_metrics(y_true, y_pred)
        assert m["accuracy"] == 1.0
        assert m["precision"] >= 0.0  # zero_division=0 sayesinde NaN değil


class TestCrossValidate:
    def test_regression_cv(self):
        rng = np.random.default_rng(42)
        x = rng.uniform(0, 10, (100, 1))
        y = (3 * x + 2 + rng.normal(0, 0.1, (100, 1))).ravel()
        result = cross_validate(LinearRegression(), x, y, cv=5)
        assert "mean" in result and "std" in result and "scores" in result
        assert len(result["scores"]) == 5
        # Linear regression neredeyse mükemmel olmalı → MAE küçük → -MAE 0'a yakın
        assert result["mean"] > -0.5

    def test_classification_cv(self):
        rng = np.random.default_rng(42)
        x = rng.uniform(0, 10, (60, 2))
        y = (x[:, 0] > 5).astype(int)
        result = cross_validate(
            DecisionTreeClassifier(random_state=42),
            x,
            y,
            cv=3,
            scoring="accuracy",
        )
        assert len(result["scores"]) == 3
        assert 0.0 <= result["mean"] <= 1.0
