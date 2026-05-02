"""
Bitki Sağlığı (PlantHealthImage) endpoint testleri
====================================================
Cycle 7'de Ayşe tarafından genişletilecek (CNN entegrasyonu) öncesi
mevcut endpoint'in regression koruması.
"""

from __future__ import annotations

from app.models.models import PlantHealthImage


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
        client.post("/api/plants/health-images?field_id=42&image_url=https://x.com/leaf.jpg")
        # DB'den doğrula
        record = db.query(PlantHealthImage).filter_by(field_id=42).first()
        assert record is not None
        assert record.image_url == "https://x.com/leaf.jpg"
