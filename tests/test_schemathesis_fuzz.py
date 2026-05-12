"""
Schemathesis Property-Based API Fuzz Tests
============================================
Schemathesis reads the FastAPI OpenAPI schema and generates random
inputs to probe every operation for crashes, schema mismatches, or
undocumented status codes. The suite is split into two parametrized
tests:

- `test_read_only_endpoints_do_not_crash` — GET endpoints (anyone)
- `test_write_endpoints_do_not_crash` — POST/PATCH/DELETE endpoints
  with `X-API-Key=dev-api-key` injected and the rate limiter disabled

Both share the same four conformance checks (no 5xx, status code in
OpenAPI, Content-Type in OpenAPI, response body matches schema). The
example budget is kept low so the run stays CI-friendly.

Run:
    pytest tests/test_schemathesis_fuzz.py -v

CI:
    `.github/workflows/ci.yml` runs the `fuzz` job as a separate step.

---

Schemathesis OpenAPI schema'sını okuyup property-based test üretir;
GET'ler ve POST/PATCH/DELETE'ler iki ayrı parametrik testte fuzzlanır.
Yazma testlerinde `X-API-Key=dev-api-key` enjekte edilir, rate limiter
devre dışı bırakılır, in-memory test DB'sine bağlanılır.
"""

from __future__ import annotations

import os

import pytest
import schemathesis
from hypothesis import HealthCheck, settings
from schemathesis.checks import not_a_server_error
from schemathesis.specs.openapi.checks import (
    content_type_conformance,
    response_schema_conformance,
    status_code_conformance,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.middleware.rate_limiter import limiter

# Load the OpenAPI schema from the FastAPI app over ASGI. TestClient is
# used internally so no live HTTP server is needed.
# ---
# OpenAPI schema'sı FastAPI app'inden ASGI modunda yüklenir.
schema = schemathesis.openapi.from_asgi("/openapi.json", app)


# Hypothesis profile — low example budget keeps the run CI-friendly.
# Writes need slightly fewer cases per op since each one hits the DB.
# `filter_too_much` is suppressed because some auth-required paths
# generate many invalid cases that Hypothesis would otherwise warn
# about.
# ---
# CI'da hızlı kalmak için düşük örnek bütçesi; yazma uçlarında her
# case DB'ye değdiği için biraz daha az ornek.
settings.register_profile(
    "schemathesis_ci",
    max_examples=10,
    deadline=None,
    suppress_health_check=[
        HealthCheck.filter_too_much,
        HealthCheck.too_slow,
        HealthCheck.data_too_large,
        HealthCheck.function_scoped_fixture,
    ],
    derandomize=True,  # deterministic seed — prevents CI flakes
)
settings.load_profile("schemathesis_ci")


_SKIP_REASON = "Fuzz suite is manual/CI-only; set SKIP_SCHEMATHESIS=1 for fast local loops."
_skipif_local = pytest.mark.skipif(os.getenv("SKIP_SCHEMATHESIS") == "1", reason=_SKIP_REASON)


# Reusable conformance check set: covers server-error, status code,
# media type and response body shape against the OpenAPI contract.
# ---
# Yeniden kullanılabilir conformance check seti.
_CONFORMANCE_CHECKS = (
    not_a_server_error,
    status_code_conformance,
    content_type_conformance,
    response_schema_conformance,
)


# ─── READ FUZZ (no auth, no state mutation) ───────────────────
read_only_schema = schema.include(method="GET")


@_skipif_local
@read_only_schema.parametrize()
def test_read_only_endpoints_do_not_crash(case):
    """Every GET endpoint stays within its OpenAPI contract under fuzz.

    ---

    Her GET endpoint dört konformite kontrolünden geçer: 5xx yok,
    documented status code, documented Content-Type, schema'ya uyan body.
    """
    case.call_and_validate(checks=_CONFORMANCE_CHECKS)


# ─── WRITE FUZZ (auth-aware, isolated in-memory DB) ───────────
# Expensive endpoints excluded — they hit external services or run
# multipart CNN inference, which would inflate CI time and risk
# flakes. The remaining 16 write operations cover the typical
# CRUD surface.
# ---
# Pahalı uçlar dışlanır (OpenWeatherMap fetch, CNN inference, clean
# pipeline) — CI süresini şişirir ve flake riski oluşturur.
_EXPENSIVE_WRITE_PATHS = (
    "/api/weather/fetch/{farm_id}",  # external API call
    "/api/weather/clean",  # pipeline run
    "/api/plants/health-images/analyze",  # multipart + CNN inference
)
write_schema = schema.include(method=["POST", "PATCH", "DELETE"]).exclude(path=list(_EXPENSIVE_WRITE_PATHS))


@pytest.fixture(scope="module", autouse=True)
def _isolated_db_and_disabled_limiter():
    """Route writes through an in-memory SQLite DB and disable rate limiter.

    Without isolation the fuzz suite would mutate the developer's
    `sfdap_dev.db`; with the rate limiter live, every test would burn
    its allowance after the first burst.

    ---

    Yazma fuzz'unu in-memory SQLite'a yönlendir ve rate limiter'ı
    kapat. Aksi halde dev DB kirlenir ve burst'ler 429'a çarpar.
    """
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def _override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    previous_limiter = limiter.enabled
    limiter.enabled = False
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        limiter.enabled = previous_limiter
        Base.metadata.drop_all(bind=test_engine)


@_skipif_local
@write_schema.parametrize()
def test_write_endpoints_do_not_crash(case):
    """Every POST/PATCH/DELETE endpoint respects its contract under fuzz.

    The `X-API-Key` header is injected so auth-protected writes reach
    the handler; the in-memory DB fixture isolates state mutations.

    ---

    `X-API-Key` her case'e eklenir; in-memory DB fixture state mutation'larını
    izole eder. Aynı dört konformite kontrolü uygulanır.
    """
    headers = dict(case.headers or {})
    headers["X-API-Key"] = "dev-api-key"
    case.headers = headers
    case.call_and_validate(checks=_CONFORMANCE_CHECKS)
