"""
End-to-End Integration Tests
==============================
Exercises several endpoints together to simulate real usage flows.

---

Birden çok ucu birlikte gerçek kullanım senaryolarında test eder.
"""


class TestSensorReadingFlow:
    """Sensör oluştur → okuma ekle → okumaları sorgula."""

    def test_full_sensor_flow(self, client):
        # 1. Sensör oluştur
        sensor = client.post(
            "/api/sensors/",
            json={"field_id": 1, "sensor_type": "soil_moisture", "serial_number": "INT-TEST-001"},
        )
        assert sensor.status_code == 201
        sensor_id = sensor.json()["id"]

        # 2. Okuma ekle
        reading = client.post(
            "/api/sensors/readings",
            json={"sensor_id": sensor_id, "moisture_percent": 45.5, "soil_temperature_c": 22.3},
        )
        assert reading.status_code == 201

        # 3. Okumaları sorgula
        readings = client.get(f"/api/sensors/{sensor_id}/readings")
        assert readings.status_code == 200
        data = readings.json()
        assert len(data) >= 1
        assert data[0]["moisture_percent"] == 45.5

    def test_sensor_create_and_delete(self, client):
        # Oluştur
        res = client.post(
            "/api/sensors/",
            json={"field_id": 1, "sensor_type": "temp", "serial_number": "INT-DEL-001"},
        )
        sid = res.json()["id"]

        # Sil
        delete_res = client.delete(f"/api/sensors/{sid}")
        assert delete_res.status_code == 200

        # Silindi mi kontrol
        get_res = client.get(f"/api/sensors/{sid}")
        assert get_res.status_code == 404


class TestWeatherFlow:
    """Hava durumu verisi ekle → istatistik sorgula."""

    def test_weather_create_and_query(self, client):
        # Veri ekle
        for i in range(3):
            res = client.post(
                "/api/weather/",
                json={"farm_id": 1, "temperature_c": 20 + i, "humidity_percent": 50 + i, "precipitation_mm": i * 2.0},
            )
            assert res.status_code == 201

        # Listele
        weather = client.get("/api/weather/?farm_id=1")
        assert weather.status_code == 200
        assert len(weather.json()) >= 3

    def test_latest_weather(self, client):
        # RBAC sonrası: farm_id sahip olunan farm olmalı; conftest default farm id=1
        client.post("/api/weather/", json={"farm_id": 1, "temperature_c": 25.0, "humidity_percent": 60.0})

        # En son kaydı al
        latest = client.get("/api/weather/latest/1")
        assert latest.status_code == 200
        assert latest.json()["temperature_c"] == 25.0


class TestIrrigationFlow:
    """Sulama tahmini → schedule oluştur → listele."""

    def test_predict_then_schedule(self, client):
        # 1. ML tahmini
        predict = client.post(
            "/api/irrigation/predict",
            json={
                "soil_moisture": 25.0,
                "soil_temperature": 28.0,
                "humidity": 40.0,
                "temperature": 35.0,
                "precipitation": 0.0,
            },
        )
        assert predict.status_code == 200
        result = predict.json()
        assert "recommended_water_liters" in result
        assert result["irrigation_needed"] is True  # Düşük nem + yüksek sıcaklık

        # 2. Schedule oluştur
        schedule = client.post(
            "/api/irrigation/schedules",
            json={
                "field_id": 1,
                "scheduled_date": "2026-04-20T10:00:00",
                "duration_min": 60,
                "water_amount_liters": result["recommended_water_liters"],
            },
        )
        assert schedule.status_code == 201

        # 3. Listele
        schedules = client.get("/api/irrigation/schedules")
        assert schedules.status_code == 200
        assert len(schedules.json()) >= 1


class TestFertilizerFlow:
    """Bitki listesi → öneri al → takvim oluştur."""

    def test_full_fertilizer_flow(self, client):
        # 1. Desteklenen bitkileri listele
        crops = client.get("/api/fertilizer/crops")
        assert crops.status_code == 200
        assert crops.json()["count"] >= 5

        # 2. Gübreleme önerisi al
        recommend = client.post(
            "/api/fertilizer/recommend",
            json={
                "crop_type": "corn",
                "soil_nitrogen": 30.0,
                "soil_phosphorus": 15.0,
                "soil_potassium": 20.0,
                "area_hectares": 10.0,
            },
        )
        assert recommend.status_code == 200
        rec = recommend.json()
        assert rec["total_fertilizer_kg"] > 0
        assert "Misir" in rec["crop_name_tr"] or "Mısır" in rec["crop_name_tr"]

        # 3. Gübreleme takvimi oluştur
        schedule = client.post(
            "/api/fertilizer/schedules",
            json={
                "crop_type": "corn",
                "planting_date": "2026-05-01",
                "area_hectares": 10.0,
                "soil_nitrogen": 30.0,
                "soil_phosphorus": 15.0,
                "soil_potassium": 20.0,
            },
        )
        assert schedule.status_code == 200
        sched = schedule.json()
        assert len(sched) == 5  # 5 fazlı takvim


class TestCrossEndpointSecurity:
    """Farklı endpoint'lerde güvenlik kontrolü."""

    def test_protected_endpoints_need_bearer(self, anon_client):
        """REBUILD Faz 1 RBAC sonrası: korumalı endpoint'ler Bearer JWT ister.

        Auth-aware endpoint'ler: sensors/farms/weather/irrigation/alerts/
        analytics. Public kalan: /api/health, /api/irrigation/predict
        (stateless ML inference).
        """
        # POST sensör — Bearer şart
        r1 = anon_client.post("/api/sensors/", json={"field_id": 1, "sensor_type": "t", "serial_number": "X"})
        assert r1.status_code == 401

        # POST weather — Bearer şart (Adım 9'a kadar X-API-Key fallback olabilir;
        # şu an sensors zaten Bearer-required pattern'inde, weather aynısı olacak)
        r2 = anon_client.post("/api/weather/", json={"farm_id": 1})
        assert r2.status_code == 401

        # GET sensör — artık Bearer şart (Faz 1 / Adım 8)
        r3 = anon_client.get("/api/sensors/")
        assert r3.status_code == 401

        # POST predict — public kalır (stateless ML)
        r4 = anon_client.post(
            "/api/irrigation/predict",
            json={
                "soil_moisture": 50,
                "soil_temperature": 20,
                "humidity": 60,
                "temperature": 25,
                "precipitation": 0,
            },
        )
        assert r4.status_code == 200


class TestAPIDocumentation:
    """OpenAPI/Swagger dokümantasyonunun eksiksiz olduğunu doğrular."""

    def test_openapi_has_all_tag_groups(self, client):
        res = client.get("/openapi.json")
        data = res.json()
        paths = list(data["paths"].keys())

        # Temel endpoint'ler mevcut
        assert "/api/health" in paths
        assert "/api/sensors/" in paths
        assert "/api/weather/" in paths
        assert "/api/irrigation/predict" in paths
        assert "/api/fertilizer/recommend" in paths
        assert "/api/fertilizer/crops" in paths
        assert "/api/analytics/summary" in paths

    def test_root_includes_dashboard_link(self, client):
        res = client.get("/")
        data = res.json()
        assert "dashboard" in data


class TestAnalyticsFlow:
    """Analytics endpoint'inin uçtan uca çalıştığını doğrular."""

    def test_analytics_summary_returns_all_sections(self, client):
        """Analytics özet endpoint'i tüm bölümleri içermelidir."""
        res = client.get("/api/analytics/summary")
        assert res.status_code == 200
        data = res.json()

        # Tüm ana bölümler mevcut
        assert "counts" in data
        assert "sensor_type_distribution" in data
        assert "farm_weather_comparison" in data
        assert "irrigation_status_distribution" in data
        assert "daily_trends" in data
        assert "sensor_reading_stats" in data
        assert "npk_profiles" in data
        assert "period_days" in data
        assert "generated_at" in data

    def test_analytics_with_sensor_data(self, client, db):
        """Sensör oluşturulunca analytics sayaçları güncellenir."""
        # Önce sensör oluştur
        sensor_data = {
            "field_id": 1,
            "sensor_type": "soil_moisture",
            "serial_number": "INT-TEST-001",
            "status": "active",
        }
        client.post(
            "/api/sensors/",
            json=sensor_data,
            headers={"X-API-Key": "dev-api-key"},
        )

        # Analytics'te sayaç güncellenmeli
        res = client.get("/api/analytics/summary")
        data = res.json()
        assert data["counts"]["sensors"] >= 1


# ─── REBUILD pivot end-to-end (v4-2) ─────────────────────────────


class TestFarmerEndToEndJourney:
    """v4-2: farmer register → login → çiftlik/tarla/sensör → uyarı tarama.

    Bir çiftçinin sıfırdan onboarding'ini tek test'te dolaş; RBAC + Bearer
    auth + ownership filtreleri birlikte çalışmalı.
    """

    def test_farmer_full_journey_register_to_alert(self, anon_client):
        # 1) Register — başarılı 201
        reg = anon_client.post(
            "/api/auth/register",
            json={
                "name": "Test Çiftçi",
                "email": "e2e-farmer@test.invalid",
                "password": "EndToEnd2026",
            },
        )
        assert reg.status_code in (200, 201)

        # 2) Login → token al
        login = anon_client.post(
            "/api/auth/login",
            json={"email": "e2e-farmer@test.invalid", "password": "EndToEnd2026"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        # 3) /me → rol farmer
        me = anon_client.get("/api/auth/me", headers=h).json()
        assert me["role"] == "farmer"
        # owned_farms_count baseline 0
        assert me["owned_farms_count"] == 0

        # 4) Farm create
        farm = anon_client.post(
            "/api/farms/",
            json={"name": "E2E Çiftlik", "city": "Konya", "region": "İç Anadolu", "area_hectares": 5.0},
            headers=h,
        )
        assert farm.status_code in (200, 201)
        farm_id = farm.json()["id"]

        # 5) Field create
        field = anon_client.post(
            "/api/fields/",
            json={"farm_id": farm_id, "name": "E2E Tarla", "soil_type": "killi", "area_hectares": 2.0},
            headers=h,
        )
        assert field.status_code in (200, 201)
        field_id = field.json()["id"]

        # 6) Field detail — kendi tarlasını görmeli
        detail = anon_client.get(f"/api/fields/{field_id}", headers=h)
        assert detail.status_code == 200
        assert detail.json()["name"] == "E2E Tarla"

        # 7) Alert check — hiç sensor okuması yok ama disease_reminder tetiklenmeli
        check = anon_client.post("/api/alerts/check", headers=h)
        assert check.status_code == 200
        types = [a["alert_type"] for a in check.json()["alerts"]]
        assert "disease_reminder" in types

        # 8) Alert listede en az 1 kayıt görünmeli (kendi farm'ı)
        alerts = anon_client.get("/api/alerts/", headers=h).json()
        assert len(alerts) >= 1


class TestRBACScopeIsolation:
    """v4-2: farmer A, farmer B'nin çiftliğine erişememeli (403)."""

    def test_farmer_cannot_access_other_farmers_farm(self, farmer_client, db):
        from app.models.models import Farm, User

        client_a, _user_a = farmer_client
        # Farmer B'yi DB'de yarat + B'ye ait bir çiftlik
        other = User(name="Diğer Çiftçi", email="other@test.invalid", password_hash="x", role="farmer")
        db.add(other)
        db.commit()
        db.refresh(other)
        farm_b = Farm(user_id=other.id, name="B Çiftlik", region="Ege")
        db.add(farm_b)
        db.commit()
        db.refresh(farm_b)

        # A, B'nin çiftliğine erişmeye çalışır
        resp = client_a.get(f"/api/farms/{farm_b.id}")
        assert resp.status_code == 403


class TestAdminUserMgmtFlow:
    """v4-2: admin yeni developer kullanıcı yarat → liste → şifre sıfırla → sil."""

    def test_admin_user_lifecycle(self, admin_client):
        client, _admin = admin_client

        # Create developer
        created = client.post(
            "/api/auth/users",
            json={"name": "E2E Dev", "email": "e2e-dev@test.invalid", "password": "DevPass2026", "role": "developer"},
        )
        assert created.status_code == 201
        dev_id = created.json()["id"]

        # List should include
        listing = client.get("/api/auth/users").json()
        assert any(u["id"] == dev_id for u in listing)

        # Password reset → developer yeni şifreyle login
        reset = client.patch(f"/api/auth/users/{dev_id}/password", json={"new_password": "DevReset2026"})
        assert reset.status_code == 200

        # Delete
        deleted = client.delete(f"/api/auth/users/{dev_id}")
        assert deleted.status_code == 204
        # GET 404
        assert client.get(f"/api/auth/users/{dev_id}").status_code == 404
