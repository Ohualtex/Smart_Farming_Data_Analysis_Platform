"""
PlantHealthImage Endpoint Tests
=================================
Covers URL-based upload, multipart `/analyze`, and the listing endpoint
backed by the heuristic / ONNX disease model.

---

URL upload, multipart analyze ve listeleme uçlarını heuristic/ONNX
model üzerinden doğrular.
"""

from __future__ import annotations

import io

from PIL import Image

from app.models.models import PlantHealthImage


def _png_bytes(color: tuple[int, int, int] = (40, 180, 60)) -> bytes:
    img = Image.new("RGB", (32, 32), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestHealthImagesList:
    def test_list_empty_returns_200(self, client):
        resp = client.get("/api/plants/health-images")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_records(self, client, db):
        db.add(
            PlantHealthImage(
                field_id=1,
                image_url="https://example.com/leaf1.jpg",
                diagnosis="healthy",
                confidence_score=0.95,
                severity="none",
            )
        )
        db.commit()
        resp = client.get("/api/plants/health-images")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["diagnosis"] == "healthy"
        assert data[0]["confidence_score"] == 0.95

    def test_list_filter_by_field_id(self, client, db):
        for fid in (1, 1, 2):
            db.add(PlantHealthImage(field_id=fid, image_url=f"u{fid}.jpg"))
        db.commit()
        resp = client.get("/api/plants/health-images?field_id=1")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_list_respects_limit(self, client, db):
        for i in range(5):
            db.add(PlantHealthImage(field_id=1, image_url=f"u{i}.jpg"))
        db.commit()
        resp = client.get("/api/plants/health-images?limit=3")
        assert resp.status_code == 200
        assert len(resp.json()) == 3


class TestHealthImageUpload:
    def test_upload_with_auth_returns_201(self, client):
        resp = client.post(
            "/api/plants/health-images?field_id=1&image_url=https://x.com/img.jpg",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] > 0
        assert "yuklendi" in data["message"].lower()

    def test_upload_without_auth_returns_401(self):
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app) as c:
            resp = c.post("/api/plants/health-images?field_id=1&image_url=https://x.com/img.jpg")
            assert resp.status_code == 401

    def test_upload_missing_field_id_returns_422(self, client):
        resp = client.post("/api/plants/health-images?image_url=https://x.com/img.jpg")
        assert resp.status_code == 422

    def test_upload_persists_to_db(self, client, db):
        # RBAC: field_id sahip olunmalı; conftest default field id=1
        client.post("/api/plants/health-images?field_id=1&image_url=https://x.com/leaf.jpg")
        record = db.query(PlantHealthImage).filter_by(field_id=1).first()
        assert record is not None
        assert record.image_url == "https://x.com/leaf.jpg"


class TestHealthImageAnalyze:
    """`/health-images/analyze` — multipart upload + heuristic CNN."""

    def test_analyze_green_image_returns_healthy(self, client):
        files = {"image": ("leaf.png", _png_bytes((40, 180, 60)), "image/png")}
        resp = client.post(
            "/api/plants/health-images/analyze",
            data={"field_id": 1},
            files=files,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["diagnosis"] == "healthy"
        assert 0.0 <= data["confidence_score"] <= 1.0
        assert data["model_version"] == "heuristic-v1"
        assert "all_scores" in data
        assert data["size_bytes"] > 0

    def test_analyze_persists_record(self, client, db):
        files = {"image": ("leaf.png", _png_bytes((40, 180, 60)), "image/png")}
        resp = client.post(
            "/api/plants/health-images/analyze",
            data={"field_id": 1},  # RBAC: default field id=1 (conftest)
            files=files,
        )
        assert resp.status_code == 201
        record = db.query(PlantHealthImage).filter_by(field_id=1).first()
        assert record is not None
        assert record.diagnosis == "healthy"

    def test_analyze_rejects_unsupported_extension(self, client):
        files = {"image": ("doc.pdf", b"%PDF-1.4 fake", "application/pdf")}
        resp = client.post(
            "/api/plants/health-images/analyze",
            data={"field_id": 1},
            files=files,
        )
        assert resp.status_code == 415

    def test_analyze_rejects_empty_file(self, client):
        files = {"image": ("empty.png", b"", "image/png")}
        resp = client.post(
            "/api/plants/health-images/analyze",
            data={"field_id": 1},
            files=files,
        )
        assert resp.status_code == 400

    def test_analyze_without_auth_returns_401(self):
        from fastapi.testclient import TestClient

        from app.main import app

        files = {"image": ("leaf.png", _png_bytes(), "image/png")}
        with TestClient(app) as c:
            resp = c.post(
                "/api/plants/health-images/analyze",
                data={"field_id": 1},
                files=files,
            )
            assert resp.status_code == 401
