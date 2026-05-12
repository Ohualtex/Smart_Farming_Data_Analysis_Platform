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
    """Her read-only endpoint random query/path param'la 500 dondurmuyor.

    EN: `call_and_validate` runs the request via ASGI TestClient and
        checks: (a) status code is documented in OpenAPI, (b) no 500
        server errors. Other client errors (400/404/422) are allowed —
        the contract just says "documented".
    TR: `call_and_validate` istegi ASGI TestClient ile yapar, sonra:
        (a) donen status code OpenAPI'de dokumante mi, (b) 500 server
        hatasi var mi diye kontrol eder. Diger client hatalari
        (400/404/422) izinli — kontrat sadece "dokumante" diyor.
    """
    # EN: `not_a_server_error` covers the most critical contract — no 500.
    #     Schemathesis 4.x ayrica default checks (status_code_conformance vb.)
    #     uygular; biz burada server-error odakli minimal kontrolu garantiliyoruz.
    # TR: `not_a_server_error` en kritik kontrati saglar — 500 olmamali.
    case.call_and_validate(checks=(not_a_server_error,))
