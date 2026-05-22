"""
SFDAP Test Konfigürasyonu
=========================
pytest fixtures: in-memory SQLite veritabanı ve FastAPI TestClient.
Rate limiter default disabled — burst test'leri kırmasın diye; özel
rate limit testleri kendi fixture'ında True'ya alıp reset eder.

REBUILD Faz 1 / Adım 6: 5 rol-aware fixture eklendi
(`anon_client`, `farmer_client`, `developer_client`, `overseer_client`,
`admin_client`). Her biri `(client, user)` tuple döner.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.middleware.rate_limiter import limiter

# Test için in-memory SQLite kullanalım (prod DB'ye dokunmaz)
SQLALCHEMY_TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Her test için temiz bir veritabanı oluşturur ve siler."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """FastAPI TestClient — gerçek DB yerine test DB kullanır.

    Rate limiter bu fixture içinde devre dışıdır; rate limit testleri
    `rate_limited_client` fixture'ını kullanmalı.
    """

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Default: rate limit kapalı; toplu test koşumlarında 429 patlamasın
    # EN: Default: rate limit disabled so bulk test runs don't trip 429
    previous = limiter.enabled
    limiter.enabled = False

    # JWT logout blacklist — modül-seviyesi `_BLACKLISTED_JTIS` global set;
    # test izolasyonu için her test öncesi temizleriz (auth_backend logout
    # testlerinden kalan jti'ler edge-case testlerine sızmasın).
    from app.routers import auth as _auth_module

    _auth_module._BLACKLISTED_JTIS.clear()

    with TestClient(app) as c:
        # X-API-Key (eski auth, legacy fallback için bazı endpoint'ler
        # hâlâ tüketebilir — şimdilik bırak)
        c.headers["X-API-Key"] = "dev-api-key"
        # ─── REBUILD Faz 1 / Adım 8: client fixture artık admin-bypass ────
        # Sensors/farms/alerts gibi router'lar artık Bearer JWT zorunlu;
        # mevcut testlerin (X-API-Key tabanlı eski paradigm) RBAC pivot'a
        # zarar görmemesi için varsayılan client otomatik admin auth ile
        # gelir + ön-seed bir farm + field oluşturur (id=1, eski testlerin
        # "field_id=1" varsayımını korur).
        from app.models.models import Farm, Field, User

        c.post(
            "/api/auth/register",
            json={"name": "Default Admin", "email": "default-admin@x.test", "password": "DefP4ssword2026"},
        )
        admin = db.query(User).filter(User.email == "default-admin@x.test").first()
        admin.role = "admin"
        # Ön-seed farm + field — id=1 garantisi için ilk insert.
        # Region/city "__internal__" — test_farms.py'nin Marmara/Akdeniz
        # filter testlerini etkilemez; yine fixture-user'a ait farm'lar
        # gerçek region'larla seed edilir.
        seed_farm = Farm(
            user_id=admin.id,
            name="__Default Farm (test conftest)__",
            region="__internal__",
            city="__internal__",
        )
        db.add(seed_farm)
        db.flush()
        seed_field = Field(farm_id=seed_farm.id, name="Default Field", soil_type="killi")
        db.add(seed_field)
        db.commit()
        tok = c.post(
            "/api/auth/login",
            json={"email": "default-admin@x.test", "password": "DefP4ssword2026"},
        ).json()["access_token"]
        c.headers["Authorization"] = f"Bearer {tok}"
        yield c

    app.dependency_overrides.clear()
    limiter.enabled = previous


@pytest.fixture(scope="function")
def rate_limited_client(db):
    """Rate limiter aktif TestClient — sadece limit testlerinde kullanılır.

    Her test öncesi limiter storage'ını temizler ki sayaçlar bulaşmasın.
    EN: Rate-limit-enabled TestClient for the limit tests; resets storage
    so counters don't leak between tests.
    """

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Limiter'ı aç ve in-memory storage'ı sıfırla
    # EN: Enable limiter and reset its in-memory storage
    limiter.enabled = True
    storage = getattr(limiter, "_storage", None)
    inner = getattr(storage, "storage", None)
    if isinstance(inner, dict):
        inner.clear()

    with TestClient(app) as c:
        c.headers["X-API-Key"] = "dev-api-key"
        # REBUILD Faz 1: sensors/farms write artık Bearer JWT zorunlu.
        # Rate-limit burst test'inin auth tarafından bloklanmaması için
        # admin Bearer token bindir.
        from app.models.models import User

        c.post(
            "/api/auth/register",
            json={"name": "RL Admin", "email": "rl-admin@x.test", "password": "RLP4ssword2026"},
        )
        admin = db.query(User).filter(User.email == "rl-admin@x.test").first()
        admin.role = "admin"
        db.commit()
        tok = c.post(
            "/api/auth/login",
            json={"email": "rl-admin@x.test", "password": "RLP4ssword2026"},
        ).json()["access_token"]
        c.headers["Authorization"] = f"Bearer {tok}"
        yield c

    app.dependency_overrides.clear()
    limiter.enabled = False


# ─── RBAC Fixtures (REBUILD Faz 1 / Adım 6) ────────────────────────
# 4-rol RBAC test fixture'ları. Her biri `(client, user)` tuple döner.
# `user.id` ve `user.email` sahiplik kontrolü için kullanılır.
#
# `anon_client` — hiçbir auth header'ı eklemez (X-API-Key bile yok);
# tamamen anonim akış testleri için.
#
# `farmer_client` / `developer_client` / `overseer_client` / `admin_client`
# — register + DB role override (farmer hariç) + login + Bearer header.
# Base `client` fixture'ından inheritance ile DB temizliği + JWT
# blacklist clear + rate limit disable miras alınır.


@pytest.fixture(scope="function")
def anon_client(db):
    """Hiçbir auth header'ı taşımayan TestClient — tamamen anonim akış için."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    previous = limiter.enabled
    limiter.enabled = False

    from app.routers import auth as _auth_module

    _auth_module._BLACKLISTED_JTIS.clear()

    with TestClient(app) as c:
        # X-API-Key veya Authorization header eklenmiyor.
        yield c

    app.dependency_overrides.clear()
    limiter.enabled = previous


def _make_role_client(client, db, role: str):
    """Helper: `client` üstüne register + role override + Bearer login bindir.

    Test isolation hijyeni için her çağrı uuid-suffixed email kullanır.
    `farmer` rolü register default'u olduğundan DB override gerekmez;
    diğer 3 rol için doğrudan `user.role = role` set edilir.
    """
    from app.models.models import User

    email = f"{role}-{uuid.uuid4().hex[:8]}@x.test"
    password = "FixtureP4ssword2026"
    client.post(
        "/api/auth/register",
        json={"name": f"{role.title()} User", "email": email, "password": password},
    )
    user = db.query(User).filter(User.email == email).first()
    if role != "farmer":
        user.role = role
        db.commit()
        db.refresh(user)
    token = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    ).json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client, user


@pytest.fixture(scope="function")
def farmer_client(client, db):
    """`(client, user)` — register edilmiş ve login olmuş farmer."""
    return _make_role_client(client, db, "farmer")


@pytest.fixture(scope="function")
def developer_client(client, db):
    """`(client, user)` — `role='developer'`'a promote edilmiş + login."""
    return _make_role_client(client, db, "developer")


@pytest.fixture(scope="function")
def overseer_client(client, db):
    """`(client, user)` — `role='overseer'`'a promote edilmiş + login."""
    return _make_role_client(client, db, "overseer")


@pytest.fixture(scope="function")
def admin_client(client, db):
    """`(client, user)` — `role='admin'`'e promote edilmiş + login."""
    return _make_role_client(client, db, "admin")
