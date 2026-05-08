"""
Plant Disease Model Tests
===========================
Heuristic mode (Pillow + HSV renk analizi) ve hata yollarını test eder.
ONNX mode için ayrı dataset/model gerektiğinden sadece "missing model
dosyası → heuristic'e düş" yolunu doğruluyoruz.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app.ml.plant_disease_model import DISEASE_CLASSES, SEVERITY_MAP, PlantDiseaseModel


def _img_bytes(color: tuple[int, int, int], size: tuple[int, int] = (64, 64)) -> bytes:
    """Solid renk PNG üret."""
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def model():
    return PlantDiseaseModel(model_path="/nonexistent/path/to/model.onnx")


class TestModelInit:
    def test_falls_back_to_heuristic_when_model_missing(self):
        m = PlantDiseaseModel(model_path="/nonexistent/path/to/model.onnx")
        assert m.session is None
        assert m.mode == "heuristic"


class TestPredictReturnShape:
    def test_returns_required_keys(self, model):
        result = model.predict(_img_bytes((40, 160, 60)))
        for key in ("diagnosis", "confidence_score", "severity", "all_scores", "model_version"):
            assert key in result

    def test_diagnosis_in_known_classes(self, model):
        result = model.predict(_img_bytes((40, 160, 60)))
        assert result["diagnosis"] in DISEASE_CLASSES + ["unknown"]

    def test_severity_matches_diagnosis(self, model):
        result = model.predict(_img_bytes((40, 160, 60)))
        if result["diagnosis"] in DISEASE_CLASSES:
            assert result["severity"] == SEVERITY_MAP[result["diagnosis"]]

    def test_confidence_in_valid_range(self, model):
        result = model.predict(_img_bytes((40, 160, 60)))
        assert 0.0 <= result["confidence_score"] <= 1.0

    def test_all_scores_includes_all_classes(self, model):
        result = model.predict(_img_bytes((40, 160, 60)))
        assert set(result["all_scores"].keys()) >= set(DISEASE_CLASSES)

    def test_model_version_is_heuristic(self, model):
        result = model.predict(_img_bytes((40, 160, 60)))
        assert result["model_version"] == "heuristic-v1"


class TestHeuristicDiagnosis:
    """Renk-bazlı kuralların doğru sınıfı seçtiğini doğrula."""

    def test_green_leaf_diagnosed_healthy(self, model):
        # Saturated green → healthy
        result = model.predict(_img_bytes((40, 180, 60)))
        assert result["diagnosis"] == "healthy"
        assert result["severity"] == "none"

    def test_white_powder_diagnosed_powdery_mildew(self, model):
        # Beyaza yakın → powdery_mildew
        result = model.predict(_img_bytes((230, 230, 230)))
        assert result["diagnosis"] == "powdery_mildew"

    def test_brown_leaf_diagnosed_blight_or_leaf_spot(self, model):
        # Kahverengi → leaf_spot veya blight
        result = model.predict(_img_bytes((110, 60, 25)))
        assert result["diagnosis"] in {"leaf_spot", "blight"}

    def test_yellow_leaf_diagnosed_mosaic_or_anthracnose(self, model):
        # Sarı → mosaic_virus / anthracnose
        result = model.predict(_img_bytes((220, 200, 40)))
        assert result["diagnosis"] in {"mosaic_virus", "anthracnose"}

    def test_color_features_exposed_in_heuristic(self, model):
        result = model.predict(_img_bytes((40, 180, 60)))
        assert "color_features" in result
        assert "green_ratio" in result["color_features"]


class TestErrorPaths:
    def test_empty_bytes_returns_error_response(self, model):
        result = model.predict(b"")
        assert result["diagnosis"] == "unknown"
        assert result["model_version"] == "error"

    def test_invalid_bytes_returns_error_response(self, model):
        result = model.predict(b"not-an-image-just-random-text")
        assert result["diagnosis"] == "unknown"
        assert result["model_version"] == "error"

    def test_deterministic_same_image_same_diagnosis(self, model):
        img = _img_bytes((40, 180, 60))
        r1 = model.predict(img)
        r2 = model.predict(img)
        assert r1["diagnosis"] == r2["diagnosis"]
        assert r1["confidence_score"] == r2["confidence_score"]
