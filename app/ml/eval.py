"""
ML Model Evaluation Utilities
===============================
Shared metric calculators + a cross-validation wrapper for trained
regression and classification models.

Built-in metrics:
- Regression: MAE, MSE, RMSE, R²
- Classification: accuracy, precision, recall, F1

Possible extensions: GridSearchCV wrapper, confusion-matrix / ROC plots,
side-by-side model comparison helper.

---

Eğitilmiş regresyon/sınıflandırma modelleri için ortak metrik
hesaplayıcıları ve cross-validation wrapper.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import cross_val_score


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """
    Regresyon modeli için temel metrikleri döndürür.

    Returns:
        {"mae": ..., "mse": ..., "rmse": ..., "r2": ...}
    """
    mse = float(mean_squared_error(y_true, y_pred))
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "mse": mse,
        "rmse": float(np.sqrt(mse)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def classification_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    average: str = "weighted",
) -> dict[str, float]:
    """
    Sınıflandırma modeli için temel metrikleri döndürür.

    Args:
        average: 'binary', 'micro', 'macro', 'weighted', 'samples'

    Returns:
        {"accuracy": ..., "precision": ..., "recall": ..., "f1": ...}
    """
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, average=average, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, average=average, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, average=average, zero_division=0)),
    }


def cross_validate(
    model: Any,
    x: np.ndarray,
    y: np.ndarray,
    cv: int = 5,
    scoring: str = "neg_mean_absolute_error",
) -> dict[str, float]:
    """
    K-fold cross-validation çalıştırır ve mean/std döndürür.

    Args:
        scoring: scikit-learn scoring string'i (regresyon için
            'neg_mean_absolute_error', sınıflandırma için 'accuracy', vb.)

    Returns:
        {"mean": ..., "std": ..., "scores": [s1, s2, ...]}
    """
    scores = cross_val_score(model, x, y, cv=cv, scoring=scoring)
    return {
        "mean": float(np.mean(scores)),
        "std": float(np.std(scores)),
        "scores": [float(s) for s in scores],
    }
