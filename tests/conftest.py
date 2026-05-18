"""
SFDAP Test Konfigürasyonu
=========================
pytest fixtures: in-memory SQLite veritabanı ve FastAPI TestClient.
Rate limiter default disabled — burst test'leri kırmasın diye; özel
rate limit testleri kendi fixture'ında True'ya alıp reset eder.
"""

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
        # Korumalı endpoint'ler için varsayılan API key ekle
        c.headers["X-API-Key"] = "dev-api-key"
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
        yield c

    app.dependency_overrides.clear()
    limiter.enabled = False
