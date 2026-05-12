"""
Schemathesis Property-Based API Fuzz Tests
============================================
Schemathesis reads the FastAPI OpenAPI schema and generates random
inputs to probe each GET endpoint for crashes, schema mismatches, or
undocumented status codes. Only read-only operations are exercised,
with a low example budget so the suite stays CI-friendly (deterministic
seed, ~10 generated cases per operation).

Run:
    pytest tests/test_schemathesis_fuzz.py -v

CI:
    `.github/workflows/ci.yml` runs the `fuzz` job as a separate step.

---

Schemathesis OpenAPI schema'sını okuyup property-based test üretir. Her
GET endpoint 500 hataları, schema uyumsuzlukları veya dokümante edilmemiş
status code'lar için denenir. Deterministik tohum + düşük örnek bütçesi
ile CI-friendly kalır.
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

from app.main import app

# Load the OpenAPI schema from the FastAPI app over ASGI. TestClient is
# used internally so no live HTTP server is needed.
# ---
# OpenAPI schema'sı FastAPI app'inden ASGI modunda yüklenir; canlı sunucu
# gerekmez, dahili TestClient kullanılır.
schema = schemathesis.openapi.from_asgi("/openapi.json", app)


# Hypothesis profile — low example budget keeps the run CI-friendly.
# `filter_too_much` is suppressed because some auth-required paths
# generate many invalid cases that Hypothesis would otherwise warn about.
# ---
# CI'da hızlı kalmak için düşük örnek bütçesi; bazı auth-gerektiren
# uçlarda filter_too_much uyarısı bilinçli olarak susturulur.
settings.register_profile(
    "schemathesis_ci",
    max_examples=10,
    deadline=None,
    suppress_health_check=[
        HealthCheck.filter_too_much,
        HealthCheck.too_slow,
        HealthCheck.data_too_large,
    ],
    derandomize=True,  # deterministic seed — prevents CI flakes
)
settings.load_profile("schemathesis_ci")


# Restrict the run to GET (read-only) operations. Write methods
# (POST/PATCH/DELETE) require auth and mutate state; they belong in a
# separate auth-aware fuzz job.
# ---
# Sadece GET (read-only) uçlar fuzzlanır. Yazma metodları auth gerektirir
# ve state mutate eder; ayrı bir auth-aware fuzz job'una uygundur.
read_only_schema = schema.include(method="GET")


@pytest.mark.skipif(
    os.getenv("SKIP_SCHEMATHESIS") == "1",
    reason="Fuzz suite is manual/CI-only; set SKIP_SCHEMATHESIS=1 for fast local loops.",
)
@read_only_schema.parametrize()
def test_read_only_endpoints_do_not_crash(case):
    """Every GET endpoint stays within its OpenAPI contract under fuzz.

    Each generated request is validated against four checks:
    - `not_a_server_error` — no 5xx escape (was the original target)
    - `status_code_conformance` — status is one declared in OpenAPI
    - `content_type_conformance` — Content-Type matches declared media
    - `response_schema_conformance` — response body matches the schema

    Together these catch silent drift where the implementation evolves
    but the schema doesn't, or vice versa.

    ---

    Her üretilen istek dört kontrolden geçer: 5xx olmamalı, status code
    OpenAPI'de dokümante olmalı, Content-Type doğru olmalı ve response
    body schema'ya uymalı. Implementasyon ile şema arasındaki sessiz
    drift'i yakalar.
    """
    case.call_and_validate(
        checks=(
            not_a_server_error,
            status_code_conformance,
            content_type_conformance,
            response_schema_conformance,
        ),
    )
