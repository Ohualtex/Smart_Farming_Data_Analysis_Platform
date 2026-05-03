"""
ModelPerformanceLog endpoint testleri
=======================================
Mehmet'in Cycle 6 görevi için skeleton testler.
"""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def sample_log():
    return {
        "model_name": "irrigation_rf",
        "prediction_data": json.dumps({"input": [30, 22, 65, 25, 2], "output": 28.4}),
        "actual_data": json.dumps({"value": 30.0}),
        "accuracy_score": 0.92,
    }


class TestLogCRUD:
    def test_list_empty(self, client):
        resp = client.get("/api/model-performance/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_log_returns_201(self, client, sample_log):
        resp = client.post("/api/model-performance/", json=sample_log)
        assert resp.status_code == 201
        assert resp.json()["model_name"] == "irrigation_rf"

    def test_create_without_auth_returns_401(self, sample_log):
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app) as c:
            resp = c.post("/api/model-performance/", json=sample_log)
            assert resp.status_code == 401

    def test_list_filter_by_model_name(self, client, sample_log):
        client.post("/api/model-performance/", json=sample_log)
        client.post("/api/model-performance/", json={**sample_log, "model_name": "plant_disease_cnn"})
        resp = client.get("/api/model-performance/?model_name=irrigation_rf")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["model_name"] == "irrigation_rf"


class TestModelSummary:
    def test_summary_for_existing_model(self, client, sample_log):
        client.post("/api/model-performance/", json=sample_log)
        client.post("/api/model-performance/", json={**sample_log, "accuracy_score": 0.88})
        resp = client.get("/api/model-performance/summary/irrigation_rf")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_name"] == "irrigation_rf"
        assert data["total_predictions"] == 2
        assert abs(data["avg_accuracy"] - 0.90) < 0.001

    def test_summary_nonexistent_model_returns_404(self, client):
        resp = client.get("/api/model-performance/summary/unknown_model")
        assert resp.status_code == 404

    def test_summary_handles_null_accuracy(self, client, sample_log):
        log = {**sample_log, "accuracy_score": None}
        client.post("/api/model-performance/", json=log)
        resp = client.get("/api/model-performance/summary/irrigation_rf")
        assert resp.status_code == 200
        assert resp.json()["avg_accuracy"] is None


class TestLogUpdate:
    def test_patch_actual_data(self, client, sample_log):
        log = {**sample_log, "actual_data": None, "accuracy_score": None}
        created = client.post("/api/model-performance/", json=log).json()
        resp = client.patch(
            f"/api/model-performance/{created['id']}",
            json={"actual_data": '{"value": 30.0}', "accuracy_score": 0.95},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["accuracy_score"] == 0.95
        assert data["actual_data"] == '{"value": 30.0}'

    def test_patch_partial(self, client, sample_log):
        created = client.post("/api/model-performance/", json=sample_log).json()
        resp = client.patch(f"/api/model-performance/{created['id']}", json={"accuracy_score": 0.5})
        assert resp.status_code == 200
        assert resp.json()["accuracy_score"] == 0.5

    def test_patch_nonexistent_returns_404(self, client):
        resp = client.patch("/api/model-performance/99999", json={"accuracy_score": 0.5})
        assert resp.status_code == 404

    def test_patch_without_auth_returns_401(self, sample_log):
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app) as c:
            resp = c.patch("/api/model-performance/1", json={"accuracy_score": 0.5})
            assert resp.status_code == 401


class TestTimeseries:
    def test_timeseries_empty_returns_empty_list(self, client):
        resp = client.get("/api/model-performance/timeseries/unknown_model")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_timeseries_groups_by_day(self, client, sample_log):
        # 3 log aynı modele
        client.post("/api/model-performance/", json=sample_log)
        client.post("/api/model-performance/", json={**sample_log, "accuracy_score": 0.85})
        resp = client.get("/api/model-performance/timeseries/irrigation_rf?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Aynı gün → tek nokta, count=2
        assert len(data) >= 1
        assert all("date" in p and "avg_accuracy" in p and "count" in p for p in data)


class TestCompare:
    def test_compare_two_models(self, client, sample_log):
        client.post("/api/model-performance/", json=sample_log)
        client.post("/api/model-performance/", json={**sample_log, "model_name": "plant_disease_cnn"})
        resp = client.get("/api/model-performance/compare?models=irrigation_rf,plant_disease_cnn")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = {d["model_name"] for d in data}
        assert names == {"irrigation_rf", "plant_disease_cnn"}

    def test_compare_includes_min_max(self, client, sample_log):
        client.post("/api/model-performance/", json={**sample_log, "accuracy_score": 0.7})
        client.post("/api/model-performance/", json={**sample_log, "accuracy_score": 0.95})
        resp = client.get("/api/model-performance/compare?models=irrigation_rf")
        assert resp.status_code == 200
        item = resp.json()[0]
        assert item["min_accuracy"] == 0.7
        assert item["max_accuracy"] == 0.95

    def test_compare_missing_models_param_returns_422(self, client):
        resp = client.get("/api/model-performance/compare")
        assert resp.status_code == 422


class TestAutoLogging:
    def test_irrigation_predict_creates_log(self, client):
        # Önce log boş olmalı
        before = client.get("/api/model-performance/?model_name=irrigation_rf").json()
        before_count = len(before)

        # Tahmin yap
        resp = client.post(
            "/api/irrigation/predict",
            json={
                "soil_moisture": 30,
                "soil_temperature": 22,
                "humidity": 60,
                "temperature": 25,
                "precipitation": 2,
            },
        )
        assert resp.status_code == 200

        # Log artmış olmalı
        after = client.get("/api/model-performance/?model_name=irrigation_rf").json()
        assert len(after) == before_count + 1
        assert after[0]["model_name"] == "irrigation_rf"
        # prediction_data JSON içerir
        import json

        pdata = json.loads(after[0]["prediction_data"])
        assert "input" in pdata
        assert "output" in pdata
        assert pdata["output"]["recommended_water_liters"] >= 0
