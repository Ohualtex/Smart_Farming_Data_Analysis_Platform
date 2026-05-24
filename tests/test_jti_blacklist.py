"""
JWT `jti` Blacklist Edge Case Testleri (shiftFinal `dec2e82` audit fix)
=======================================================================
Logout sırasında token-string yerine `jti` claim'i blacklist'e atılıyor —
aynı saniyede aynı user için üretilen iki token'ın `{sub, iat, exp}`
payload'ı byte-identical olsa bile her token benzersiz `jti` ile farklı
kalır. Bu paket o akışın edge case'lerini sabitler:

1. Modern token: `jti` payload'da, logout sonrası blacklist eşleşmesi
2. Legacy token: `jti` yok → blacklist KONTROLÜ atlanır (yumuşak geçiş)
3. Tampered `jti`: signature kırık → 401
4. İki ardışık login farklı `jti` üretir (zaman precision'dan bağımsız)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.config import settings
from app.routers import auth as _auth_module


def _create_legacy_token(user_id: int) -> str:
    """`jti` İÇERMEYEN bir JWT üret — eski client'ların tokenı simüle eder."""
    payload = {
        "sub": str(user_id),
        "iat": int(datetime.now(UTC).timestamp()),
        "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        # jti YOK
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _register_and_login(client, email: str = "jti-test@sfdap.test") -> tuple[str, dict]:
    """Helper: register + login → (token, payload)."""
    client.post(
        "/api/auth/register",
        json={"name": "JTI Test", "email": email, "password": "JtiP4sswordZZ"},
    )
    res = client.post(
        "/api/auth/login",
        json={"email": email, "password": "JtiP4sswordZZ"},
    )
    token = res.json()["access_token"]
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    return token, payload


class TestJtiPayloadContract:
    """Yeni token'lar `jti` claim'ini içerir mi?"""

    def test_login_response_jwt_contains_jti(self, client):
        """`/api/auth/login` döndüğü token'da jti olmalı."""
        _, payload = _register_and_login(client)
        assert "jti" in payload
        assert len(payload["jti"]) > 0

    def test_jti_is_uuid_hex_format(self, client):
        """`uuid.uuid4().hex` formatı → 32 hex karakter, dash yok."""
        _, payload = _register_and_login(client, email="jti-fmt@sfdap.test")
        jti = payload["jti"]
        assert len(jti) == 32
        assert "-" not in jti
        # Sadece hex karakterler
        int(jti, 16)  # ValueError fırlatmazsa OK

    def test_two_logins_produce_distinct_jtis(self, client):
        """Aynı kullanıcının iki ardışık login'i farklı jti üretir."""
        email = "jti-double@sfdap.test"
        _, p1 = _register_and_login(client, email=email)
        # Aynı user, ikinci login
        r = client.post("/api/auth/login", json={"email": email, "password": "JtiP4sswordZZ"})
        token2 = r.json()["access_token"]
        p2 = jwt.decode(token2, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        # iat aynı saniyede olabilir (deterministic test) — jti farklı olmalı
        assert p1["jti"] != p2["jti"]


class TestJtiBlacklistInvalidation:
    """Logout → jti blacklist; aynı jti reddedilmeli."""

    def test_logout_blacklists_jti_specifically(self, client):
        """Logout sonrası token'daki jti `_BLACKLISTED_JTIS`'de görünür."""
        token, payload = _register_and_login(client, email="jti-blacklist@sfdap.test")
        # Geçerli
        assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200
        # Logout
        client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
        # Modül-seviye set'te jti şimdi var
        assert payload["jti"] in _auth_module._BLACKLISTED_JTIS
        # Aynı token artık reddedilir
        assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401

    def test_logout_does_not_blacklist_other_user_tokens(self, client):
        """Bir kullanıcının logout'u başka kullanıcının token'ını etkilememeli."""
        # User A login + logout
        token_a, _ = _register_and_login(client, email="user-a@sfdap.test")
        client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token_a}"})
        # User B login (farklı jti)
        token_b, _ = _register_and_login(client, email="user-b@sfdap.test")
        # B'nin token'ı blacklist'te değil → 200 alır
        assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_b}"}).status_code == 200


class TestJtiLegacyTolerance:
    """`jti` yokken (eski client) eski davranışla uyumlu."""

    def test_legacy_token_without_jti_still_validates(self, client):
        """Eski format token (jti'siz) `/me`'de 200 dönmeli."""
        # Önce bir kullanıcı yarat — login → DB'de bir kayıt olsun
        email = "legacy@sfdap.test"
        client.post(
            "/api/auth/register",
            json={"name": "Legacy User", "email": email, "password": "LegP4sswordZZ"},
        )
        # Şimdi DB'deki user_id'yi al
        from app.database import Base

        # client fixture'ın db oturumunu doğrudan al
        # Pratik: test, /login ile user_id öğrenebiliriz
        res = client.post("/api/auth/login", json={"email": email, "password": "LegP4sswordZZ"})
        login_payload = jwt.decode(
            res.json()["access_token"],
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id = int(login_payload["sub"])
        # Şimdi jti'siz legacy token
        legacy_token = _create_legacy_token(user_id)
        # `/me` 200 dönmeli — jti yokken blacklist check atlanır
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {legacy_token}"})
        assert r.status_code == 200
        # Base'in import edildiğini sustur (linter happy)
        assert Base is not None

    def test_legacy_token_never_blacklisted(self, client):
        """jti'siz token bir kez logout edilse bile bir sonraki istek 200 alır
        (blacklist check'i jti'ye dayanır; jti yoksa atlanır)."""
        email = "legacy2@sfdap.test"
        client.post(
            "/api/auth/register",
            json={"name": "Legacy 2", "email": email, "password": "LegP4sswordZZ"},
        )
        res = client.post("/api/auth/login", json={"email": email, "password": "LegP4sswordZZ"})
        user_id = int(
            jwt.decode(
                res.json()["access_token"],
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )["sub"]
        )
        legacy_token = _create_legacy_token(user_id)
        # Logout legacy token ile — jti yok, blacklist'e ekleyemeyiz
        client.post("/api/auth/logout", headers={"Authorization": f"Bearer {legacy_token}"})
        # Aynı legacy token hâlâ çalışır (jti yokluğu = "asla blacklist'lenmemiş")
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {legacy_token}"})
        assert r.status_code == 200


class TestTamperedJwt:
    """Signature kırılınca jti check'ten önce JWTError fırlatılmalı."""

    def test_tampered_signature_rejected_before_jti_check(self, client):
        """Signature segment'i değiştirildiğinde 401 (v4-6: tek-karakter
        strategy base64url'da padding-equivalent çakışma riskli olduğu için
        signature'ı tamamen sahteleştirilen string ile değiştir)."""
        token, _ = _register_and_login(client, email="tamper-jti@sfdap.test")
        # JWT format: header.payload.signature → signature'ı tamamen sahtele
        parts = token.split(".")
        assert len(parts) == 3, "JWT 3 segment olmalı"
        tampered = f"{parts[0]}.{parts[1]}.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered}"})
        assert r.status_code == 401

    def test_malformed_token_rejected(self, client):
        """Tamamen bozuk (3 segmentli değil) token → 401."""
        r = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
        assert r.status_code == 401


@pytest.fixture(autouse=True)
def _clear_blacklist_after_test():
    """Her test sonrası `_BLACKLISTED_JTIS`'i temizle — diğer test
    dosyalarına sızıntı olmasın (conftest.py her test öncesi de temizliyor;
    burası ek savunma)."""
    yield
    _auth_module._BLACKLISTED_JTIS.clear()
