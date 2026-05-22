"""
Sulama (Irrigation) Endpoint Testleri — REBUILD Faz 4 RBAC + onay/status
==========================================================================
POST  /api/irrigation/predict                  (public — stateless ML)
GET   /api/irrigation/schedules                 (Bearer + rol-aware scope)
GET   /api/irrigation/schedules/count           (Bearer + rol-aware scope)
POST  /api/irrigation/schedules                 (onay — write + field ownership)
PATCH /api/irrigation/schedules/{id}/status     (durum — write + field ownership)

Not: schedule endpoint'leri artık field ownership ister. `client` fixture
(conftest) admin Bearer + ön-seed Field id=1 ile gelir → admin bypass sayesinde
mevcut testler çalışır. field_id=1 dışı senaryolar db fixture ile seed'lenir.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.models.models import Farm, Field, IrrigationSchedule

SAMPLE_PREDICTION_REQUEST = {
    "soil_moisture": 35.0,
    "soil_temperature": 18.5,
    "humidity": 60.0,
    "temperature": 25.0,
    "precipitation": 0.0,
}

SAMPLE_SCHEDULE = {
    "field_id": 1,
    "scheduled_date": "2026-04-10T08:00:00",
    "duration_min": 45,
    "water_amount_liters": 500.0,
}


def _seed_field(db, user_id: int, name: str = "Test Tarla") -> int:
    """Bir kullanıcıya ait Farm→Field zinciri kur, field id döndür."""
    farm = Farm(user_id=user_id, name=f"{name} Çiftlik", region="Ege")
    db.add(farm)
    db.flush()
    field = Field(farm_id=farm.id, name=name, soil_type="killi")
    db.add(field)
    db.commit()
    return field.id


# ───── POST /api/irrigation/predict (public) ─────────────────────────────────
class TestIrrigationPredict:
    def test_predict_returns_200(self, client):
        response = client.post("/api/irrigation/predict", json=SAMPLE_PREDICTION_REQUEST)
        assert response.status_code == 200

    def test_predict_response_has_recommendation(self, client):
        response = client.post("/api/irrigation/predict", json=SAMPLE_PREDICTION_REQUEST)
        data = response.json()
        assert "irrigation_needed" in data
        assert "message" in data

    def test_predict_response_has_confidence(self, client):
        response = client.post("/api/irrigation/predict", json=SAMPLE_PREDICTION_REQUEST)
        assert "confidence" in response.json()

    def test_predict_with_high_moisture(self, client):
        request = {**SAMPLE_PREDICTION_REQUEST, "soil_moisture": 85.0}
        assert client.post("/api/irrigation/predict", json=request).status_code == 200

    def test_predict_with_low_moisture(self, client):
        request = {**SAMPLE_PREDICTION_REQUEST, "soil_moisture": 10.0}
        assert client.post("/api/irrigation/predict", json=request).status_code == 200

    def test_predict_missing_fields_returns_422(self, client):
        assert client.post("/api/irrigation/predict", json={"soil_moisture": 35.0}).status_code == 422

    def test_predict_invalid_moisture_value(self, client):
        invalid = {**SAMPLE_PREDICTION_REQUEST, "soil_moisture": "yüksek"}
        assert client.post("/api/irrigation/predict", json=invalid).status_code == 422

    def test_predict_public_no_auth_needed(self, anon_client):
        """Predict stateless ML — anon erişebilir."""
        assert anon_client.post("/api/irrigation/predict", json=SAMPLE_PREDICTION_REQUEST).status_code == 200


# ───── GET /api/irrigation/schedules (admin client — bypass) ─────────────────
class TestGetSchedules:
    def test_get_schedules_empty_returns_200(self, client):
        response = client.get("/api/irrigation/schedules")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_schedules_after_create(self, client):
        client.post("/api/irrigation/schedules", json=SAMPLE_SCHEDULE)
        assert len(client.get("/api/irrigation/schedules").json()) >= 1

    def test_get_schedules_field_id_filter(self, client, db):
        second = _seed_field(db, user_id=1, name="İkinci")  # admin owns (bypass anyway)
        client.post("/api/irrigation/schedules", json=SAMPLE_SCHEDULE)  # field 1
        client.post("/api/irrigation/schedules", json={**SAMPLE_SCHEDULE, "field_id": second})
        response = client.get("/api/irrigation/schedules?field_id=1")
        assert all(item["field_id"] == 1 for item in response.json())


# ───── POST /api/irrigation/schedules (admin) ────────────────────────────────
class TestCreateSchedule:
    def test_create_schedule_returns_201(self, client):
        assert client.post("/api/irrigation/schedules", json=SAMPLE_SCHEDULE).status_code == 201

    def test_create_schedule_has_id(self, client):
        assert "id" in client.post("/api/irrigation/schedules", json=SAMPLE_SCHEDULE).json()

    def test_create_schedule_stores_water(self, client):
        data = client.post("/api/irrigation/schedules", json=SAMPLE_SCHEDULE).json()
        assert data["water_amount_liters"] == SAMPLE_SCHEDULE["water_amount_liters"]


# ───── /schedules/count + skip pagination (admin) ────────────────────────────
class TestIrrigationPagination:
    def test_count_empty_db(self, client):
        response = client.get("/api/irrigation/schedules/count")
        assert response.status_code == 200
        assert response.json() == {"total": 0}

    def test_count_reflects_created_schedules(self, client):
        for _ in range(3):
            client.post("/api/irrigation/schedules", json=SAMPLE_SCHEDULE)
        assert client.get("/api/irrigation/schedules/count").json()["total"] == 3

    def test_count_with_field_id_filter(self, client, db):
        second = _seed_field(db, user_id=1, name="İkinci")
        client.post("/api/irrigation/schedules", json={**SAMPLE_SCHEDULE, "field_id": 1})
        client.post("/api/irrigation/schedules", json={**SAMPLE_SCHEDULE, "field_id": 1})
        client.post("/api/irrigation/schedules", json={**SAMPLE_SCHEDULE, "field_id": second})
        total = client.get("/api/irrigation/schedules/count").json()["total"]
        filtered = client.get("/api/irrigation/schedules/count?field_id=1").json()["total"]
        assert total == 3
        assert filtered == 2

    def test_skip_limit_returns_correct_slice(self, client):
        for i in range(5):
            payload = {**SAMPLE_SCHEDULE, "scheduled_date": f"2026-04-{10 + i:02d}T08:00:00"}
            client.post("/api/irrigation/schedules", json=payload)
        data = client.get("/api/irrigation/schedules?skip=2&limit=2").json()
        assert len(data) == 2

    def test_negative_skip_rejected(self, client):
        assert client.get("/api/irrigation/schedules?skip=-1&limit=10").status_code == 422

    def test_limit_over_max_rejected(self, client):
        assert client.get("/api/irrigation/schedules?limit=501").status_code == 422


# ───── REBUILD Faz 4 — RBAC + onay/status ────────────────────────────────────
class TestIrrigationRBAC:
    def test_anon_get_schedules_401(self, anon_client):
        assert anon_client.get("/api/irrigation/schedules").status_code == 401

    def test_anon_create_schedule_401(self, anon_client):
        assert anon_client.post("/api/irrigation/schedules", json=SAMPLE_SCHEDULE).status_code == 401

    def test_farmer_creates_on_own_field_201(self, farmer_client, db):
        client, user = farmer_client
        fid = _seed_field(db, user_id=user.id)
        r = client.post("/api/irrigation/schedules", json={**SAMPLE_SCHEDULE, "field_id": fid})
        assert r.status_code == 201

    def test_farmer_cannot_create_on_others_field_403(self, farmer_client, db):
        client, _ = farmer_client
        other = _seed_field(db, user_id=9999)
        r = client.post("/api/irrigation/schedules", json={**SAMPLE_SCHEDULE, "field_id": other})
        assert r.status_code == 403

    def test_create_on_missing_field_404(self, farmer_client):
        client, _ = farmer_client
        r = client.post("/api/irrigation/schedules", json={**SAMPLE_SCHEDULE, "field_id": 999999})
        assert r.status_code == 404

    def test_farmer_sees_only_own_schedules(self, farmer_client, db):
        client, user = farmer_client
        own = _seed_field(db, user_id=user.id, name="Benim")
        other = _seed_field(db, user_id=9999, name="Başka")
        client.post("/api/irrigation/schedules", json={**SAMPLE_SCHEDULE, "field_id": own})
        # Başka kullanıcının field'ına schedule (db direkt — API 403 verirdi)
        db.add(IrrigationSchedule(field_id=other, scheduled_date=datetime.now(UTC), status="pending"))
        db.commit()
        rows = client.get("/api/irrigation/schedules").json()
        assert all(r["field_id"] == own for r in rows)

    def test_overseer_cannot_create_403(self, overseer_client, db):
        client, _ = overseer_client
        fid = _seed_field(db, user_id=1)
        r = client.post("/api/irrigation/schedules", json={**SAMPLE_SCHEDULE, "field_id": fid})
        assert r.status_code == 403

    def test_developer_cannot_create_403(self, developer_client, db):
        client, _ = developer_client
        fid = _seed_field(db, user_id=1)
        r = client.post("/api/irrigation/schedules", json={**SAMPLE_SCHEDULE, "field_id": fid})
        assert r.status_code == 403

    def test_patch_status_owner_200(self, farmer_client, db):
        client, user = farmer_client
        fid = _seed_field(db, user_id=user.id)
        sid = client.post("/api/irrigation/schedules", json={**SAMPLE_SCHEDULE, "field_id": fid}).json()["id"]
        r = client.patch(f"/api/irrigation/schedules/{sid}/status", json={"status": "completed"})
        assert r.status_code == 200
        assert r.json()["status"] == "completed"

    def test_patch_status_invalid_value_422(self, farmer_client, db):
        client, user = farmer_client
        fid = _seed_field(db, user_id=user.id)
        sid = client.post("/api/irrigation/schedules", json={**SAMPLE_SCHEDULE, "field_id": fid}).json()["id"]
        r = client.patch(f"/api/irrigation/schedules/{sid}/status", json={"status": "bilinmeyen"})
        assert r.status_code == 422

    def test_patch_status_missing_schedule_404(self, farmer_client):
        client, _ = farmer_client
        r = client.patch("/api/irrigation/schedules/999999/status", json={"status": "completed"})
        assert r.status_code == 404

    def test_patch_status_others_schedule_403(self, farmer_client, db):
        client, _ = farmer_client
        other = _seed_field(db, user_id=9999)
        sched = IrrigationSchedule(field_id=other, scheduled_date=datetime.now(UTC), status="pending")
        db.add(sched)
        db.commit()
        r = client.patch(f"/api/irrigation/schedules/{sched.id}/status", json={"status": "completed"})
        assert r.status_code == 403
