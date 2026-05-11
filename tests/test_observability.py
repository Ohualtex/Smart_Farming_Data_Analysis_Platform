"""
Observability Stack Tests
============================
shiftFinal — A2 paketi (Mehmet) için testler:
- Sentry init (DSN boş vs dolu)
- Prometheus /metrics endpoint
- JSON log formatter
- Request ID middleware (X-Request-ID header)

EN: Tests for the A2 observability bundle — Sentry init contract,
Prometheus exposition, JSON log format, and request_id propagation.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.config import Settings
from app.core.sentry import init_sentry

# ─── 1. Sentry init ──────────────────────────────────────────────────


class TestSentryInit:
    """`init_sentry()` davranışı — DSN boş ise no-op, dolu ise SDK çağrılır."""

    def test_empty_dsn_returns_false(self, monkeypatch):
        """Default config'de SENTRY_DSN boş → no-op."""
        from app.core import sentry as sentry_module

        # Default Settings (DSN="")
        fake_settings = Settings(SENTRY_DSN="")
        monkeypatch.setattr(sentry_module, "settings", fake_settings)
        assert init_sentry() is False

    def test_dsn_set_triggers_sdk_init(self, monkeypatch):
        """SENTRY_DSN set ise sentry_sdk.init çağrılmalı."""
        from app.core import sentry as sentry_module

        fake_settings = Settings(
            SENTRY_DSN="https://fake@sentry.io/123",
            SENTRY_ENVIRONMENT="test",
        )
        monkeypatch.setattr(sentry_module, "settings", fake_settings)

        with patch.object(sentry_module.sentry_sdk, "init") as mock_init:
            result = init_sentry()
            assert result is True
            mock_init.assert_called_once()
            kwargs = mock_init.call_args.kwargs
            assert kwargs["dsn"] == "https://fake@sentry.io/123"
            assert kwargs["environment"] == "test"
            assert kwargs["send_default_pii"] is False

    def test_sentry_environment_falls_back_to_environment(self, monkeypatch):
        """SENTRY_ENVIRONMENT boşsa ENVIRONMENT kullanılmalı."""
        from app.core import sentry as sentry_module

        fake_settings = Settings(
            SENTRY_DSN="https://fake@sentry.io/123",
            SENTRY_ENVIRONMENT="",
            ENVIRONMENT="development",
        )
        monkeypatch.setattr(sentry_module, "settings", fake_settings)

        with patch.object(sentry_module.sentry_sdk, "init") as mock_init:
            init_sentry()
            assert mock_init.call_args.kwargs["environment"] == "development"


# ─── 2. Prometheus /metrics endpoint ─────────────────────────────────


class TestPrometheusMetrics:
    """`/metrics` endpoint Prometheus text format döndürmeli."""

    def test_metrics_endpoint_returns_200(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_content_type_prometheus(self, client):
        """Content-Type Prometheus exposition format'ı olmalı."""
        response = client.get("/metrics")
        # CONTENT_TYPE_LATEST → "text/plain; version=0.0.4; charset=utf-8"
        assert "text/plain" in response.headers["content-type"]

    def test_metrics_body_includes_known_metric_names(self, client):
        """En azından bir kez request atıldıktan sonra body'de metric'ler görünmeli."""
        # Önce bir request at — counter inc'lensin
        client.get("/api/health")
        response = client.get("/metrics")
        body = response.text
        assert "sfdap_http_requests_total" in body
        assert "sfdap_http_request_duration_seconds" in body

    def test_metrics_records_request_with_labels(self, client):
        """Spesifik bir endpoint'e atılan istek doğru label'larla kaydedilmeli."""
        client.get("/api/health")
        body = client.get("/metrics").text
        # method="GET", path="/api/health", status="200" content'i içermeli
        assert 'method="GET"' in body
        assert 'path="/api/health"' in body
        assert 'status="200"' in body

    def test_metrics_endpoint_itself_not_instrumented(self, client):
        """/metrics endpoint'inin kendisi metric'e yansımamalı (recursive değil)."""
        # /metrics'i 3 kez çağır
        for _ in range(3):
            client.get("/metrics")
        body = client.get("/metrics").text
        # body'de /metrics path label'ı OLMAMALI
        assert 'path="/metrics"' not in body


# ─── 3. JSON log formatter ────────────────────────────────────────────


class TestJsonLogFormatter:
    """`_json_formatter` her log record'unu tek JSON satırına çevirmeli."""

    def test_json_formatter_emits_valid_json(self):
        # Loguru record dict mock'la (gerçek record şemasına uygun)
        from datetime import UTC, datetime

        from app.core.logger import _json_formatter

        record = {
            "time": datetime.now(UTC),
            "level": type("L", (), {"name": "INFO"})(),
            "name": "test.module",
            "function": "test_func",
            "line": 42,
            "message": "Test log message — Türkçe karakter testi",
            "extra": {"request_id": "abc123"},
            "exception": None,
        }
        line = _json_formatter(record)
        # Çıktı tek satır + valid JSON olmalı
        assert line.endswith("\n")
        parsed = json.loads(line.strip())
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Test log message — Türkçe karakter testi"
        assert parsed["extra"]["request_id"] == "abc123"
        assert parsed["function"] == "test_func"

    def test_json_formatter_includes_exception(self):
        from datetime import UTC, datetime

        from app.core.logger import _json_formatter

        record = {
            "time": datetime.now(UTC),
            "level": type("L", (), {"name": "ERROR"})(),
            "name": "test.module",
            "function": "boom",
            "line": 99,
            "message": "Something failed",
            "extra": {},
            "exception": type("E", (), {"type": ValueError, "value": ValueError("boom!")})(),
        }
        line = _json_formatter(record)
        parsed = json.loads(line.strip())
        assert parsed["exception"]["type"] == "ValueError"
        assert "boom!" in parsed["exception"]["value"]


# ─── 4. Request ID middleware ────────────────────────────────────────


class TestRequestIdPropagation:
    """RequestLoggerMiddleware her response'a `X-Request-ID` ekleyip
    istemcinin gönderdiği ID'yi onurlandırmalı."""

    def test_response_includes_x_request_id_header(self, client):
        response = client.get("/api/health")
        assert "X-Request-ID" in response.headers
        # UUID hex format (32 char) veya hex+dash
        assert len(response.headers["X-Request-ID"]) >= 16

    def test_client_supplied_request_id_is_honored(self, client):
        """İstemci `X-Request-ID` gönderirse middleware o ID'yi tekrar yansıtmalı."""
        custom_id = "client-trace-id-12345"
        response = client.get("/api/health", headers={"X-Request-ID": custom_id})
        assert response.headers["X-Request-ID"] == custom_id

    def test_consecutive_requests_get_unique_ids(self, client):
        """İki ardışık request farklı request_id almalı (UUID benzersiz)."""
        r1 = client.get("/api/health")
        r2 = client.get("/api/health")
        assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"]


# ─── 5. Log format env switch ─────────────────────────────────────────


class TestLogFormatSwitch:
    """`LOG_FORMAT` env değişimi setup_logging davranışını etkilemeli."""

    def test_log_format_default_is_text(self):
        """Default Settings text formatı kullanmalı."""
        s = Settings()
        assert s.LOG_FORMAT.lower() == "text"

    def test_log_format_json_recognized(self):
        """LOG_FORMAT=json explicit set edildiğinde okunmalı."""
        s = Settings(LOG_FORMAT="json")
        assert s.LOG_FORMAT.lower() == "json"


@pytest.fixture(autouse=True)
def _reset_prometheus_registry():
    """Her test arasında Prometheus registry sıfırlanmaz (in-memory state)
    ama test'ler counter delta'larını mutlak değil göreceli kontrol ediyor."""
    # Hiçbir şey yapma — sadece dokümantasyon için fixture
    return
