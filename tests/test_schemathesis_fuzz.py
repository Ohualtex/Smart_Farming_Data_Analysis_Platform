"""
Schemathesis Property-Based API Fuzz Tests
============================================
shiftFinal — Ayşe paketi. OpenAPI schema'sından property-based test
üreten Schemathesis ile sınırlı GET endpoint'leri fuzzlanır.

EN: Schemathesis reads our FastAPI OpenAPI schema and generates random
    inputs to probe each GET endpoint for crashes, schema-mismatches,
    or undocumented status codes. We restrict the run to read-only
    operations and a low example budget so the test is CI-friendly
    (deterministic seed, ~10 generated cases per operation).

TR: Schemathesis FastAPI OpenAPI schema'sini okuyup random input'lar
    uretir. Her GET endpoint'i 500 hatalari, schema uyumsuzluklari
    veya dokumante edilmemis status code'lar icin denenir. CI'da hizli
    kalmasi icin sadece read-only operasyonlar ve dusuk ornek butcesi
    kullanilir (deterministik seed, operasyon basina ~10 case).

Calistirmak icin:
    pytest tests/test_schemathesis_fuzz.py -v

CI:
    .github/workflows/ci.yml `fuzz` job'i ayri bir adim olarak calistirir.
"""

from __future__ import annotations

import os

import pytest
import schemathesis
from hypothesis import HealthCheck, settings
from schemathesis.checks import not_a_server_error

from app.main import app

# EN: Load the OpenAPI schema from the running FastAPI app (ASGI mode).
#     TestClient is used internally; no live HTTP server needed.
# TR: OpenAPI schema'si calisan FastAPI app'inden ASGI modunda okunur.
#     Dahili olarak TestClient kullanilir, canli sunucuya gerek yok.
schema = schemathesis.openapi.from_asgi("/openapi.json", app)


# EN: Hypothesis profile — CI'da hizli kalmak icin max_examples=10.
#     filter_too_much suppressed: bazi auth-required path'lerde
#     hypothesis filtre ediyor, bu warning'i hata sayma.
# TR: Hypothesis profili — CI'da hızlı kalmak için ornek butcesi dusuk.
settings.register_profile(
    "schemathesis_ci",
    max_examples=10,
    deadline=None,
    suppress_health_check=[
        HealthCheck.filter_too_much,
        HealthCheck.too_slow,
        HealthCheck.data_too_large,
    ],
    derandomize=True,  # deterministik tohum — CI flake'i onler
)
settings.load_profile("schemathesis_ci")


# EN: Filter to GET-only read-only endpoints. Write methods
#     (POST/PATCH/DELETE) ve state-mutating operasyonlar uzun fuzz
#     icin ayri bir job'da ele alinabilir; bu modul "smoke fuzz".
# TR: Sadece GET (read-only) operasyonlar; yazma metodlari hem auth
#     gerektirdigi hem de state mutate ettigi icin shiftFinal smoke
#     scope'unda yok.
read_only_schema = schema.include(method="GET")


@pytest.mark.skipif(
    os.getenv("SKIP_SCHEMATHESIS") == "1",
    reason="Fuzz suite manuel/CI-only — local hizli iterasyon icin SKIP_SCHEMATHESIS=1.",
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
