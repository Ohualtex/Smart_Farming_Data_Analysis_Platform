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
