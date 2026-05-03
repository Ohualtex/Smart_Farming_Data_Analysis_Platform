"""
Plant Disease Model (skeleton stub) testleri
==============================================
Cycle 7'de Ayşe gerçek CNN ile değiştirecek; bu testler stub davranışını
sabitler — deterministik tahmin, valid sınıf, makul güven aralığı.
"""

from __future__ import annotations

from app.ml.plant_disease_model import DISEASE_CLASSES, SEVERITY_MAP, PlantDiseaseModel


class TestStubPredict:
    def setup_method(self):
        self.model = PlantDiseaseModel()

    def test_returns_required_keys(self):
        result = self.model.predict(b"sample_image_bytes")
        for key in ("diagnosis", "confidence_score", "severity", "all_scores", "model_version"):
            assert key in result

    def test_diagnosis_in_known_classes(self):
        result = self.model.predict(b"sample_image_bytes")
        assert result["diagnosis"] in DISEASE_CLASSES

    def test_severity_matches_diagnosis(self):
        result = self.model.predict(b"sample_image_bytes")
        assert result["severity"] == SEVERITY_MAP[result["diagnosis"]]

    def test_confidence_in_valid_range(self):
        result = self.model.predict(b"sample_image_bytes")
        assert 0.0 <= result["confidence_score"] <= 1.0

    def test_deterministic_same_input_same_output(self):
        r1 = self.model.predict(b"deterministic_test_bytes")
        r2 = self.model.predict(b"deterministic_test_bytes")
        assert r1["diagnosis"] == r2["diagnosis"]
        assert r1["confidence_score"] == r2["confidence_score"]

    def test_different_input_likely_different_output(self):
        r1 = self.model.predict(b"input_a_xxxxxxxx")
        r2 = self.model.predict(b"input_b_yyyyyyyy")
        # En azından biri farklı olmalı
        assert (r1["diagnosis"] != r2["diagnosis"]) or (r1["confidence_score"] != r2["confidence_score"])

    def test_all_scores_includes_all_classes(self):
        result = self.model.predict(b"sample_image_bytes")
        assert set(result["all_scores"].keys()) == set(DISEASE_CLASSES)

    def test_model_version_is_stub(self):
        result = self.model.predict(b"sample_image_bytes")
        # Cycle 7'de gerçek model gelince bu değer değişecek
        assert result["model_version"] == "stub-v0"


class TestModelInit:
    def test_model_loads_in_stub_mode_when_file_missing(self):
        model = PlantDiseaseModel(model_path="/nonexistent/path/to/model.onnx")
        assert model.session is None
        # Stub modda hala predict edebilmeli
        result = model.predict(b"test")
        assert result["model_version"] == "stub-v0"
