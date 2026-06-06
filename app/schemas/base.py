"""
SFDAP Şema Temelleri (paylaşılan parçalar)
==========================================
Domain modüllerinin ortak kullandığı yardımcılar: UTC datetime serializer,
SQLite-güvenli int sınırı ve bunların `Annotated` tipleri.

EN: Shared building blocks for the SFDAP schema package — UTC datetime
serializer, SQLite-safe int bound and their `Annotated` types.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import Field, PlainSerializer


def _serialize_utc(value: datetime) -> str:
    """Always emit RFC 3339 `date-time` with a UTC suffix.

    SQLAlchemy returns naive datetimes from SQLite; without this
    serializer the JSON output ("2026-05-02T22:48:07.191981") fails
    OpenAPI `format: date-time` validation (no timezone offset).
    Naive values are interpreted as UTC.

    ---

    SQLAlchemy SQLite'tan tz'siz datetime döndürür; bu serializer hep
    UTC suffix'li ISO 8601 üretip OpenAPI `date-time` kontratıyla uyumlu
    JSON çıkarır.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


UtcDateTime = Annotated[
    datetime,
    PlainSerializer(_serialize_utc, return_type=str, when_used="json"),
]

# SQLite INTEGER is signed 64-bit: max = 2**63 - 1 = 9_223_372_036_854_775_807.
# Without this bound Schemathesis / hand-crafted clients can submit ints
# beyond that and trip an OverflowError → 500 inside SQLAlchemy's
# `do_execute`. With the bound Pydantic returns 422 cleanly.
# Mirrors the Query-side `MAX_SKIP` guard added in `7e49bef` for skip/limit;
# this is the body-side companion (caught by POST /api/weather/ fuzz).
SQLITE_INT_MAX = 9_223_372_036_854_775_807
SqliteSafeInt = Annotated[int, Field(le=SQLITE_INT_MAX, ge=-SQLITE_INT_MAX - 1)]
