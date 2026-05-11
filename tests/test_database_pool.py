"""
Database Engine Pool Configuration Tests
==========================================
shiftFinal — Emirhan A4 paketi. `_build_engine_kwargs()` davranışını test
eder: SQLite için pool ayarları yok, PostgreSQL/MySQL için var.

EN: Verifies that engine kwargs change based on DATABASE_URL dialect —
SQLite skips pool tuning (single-connection model), server DBs apply
pool_size/max_overflow/pool_pre_ping/pool_recycle from settings.
"""

from __future__ import annotations

from unittest.mock import patch

from app.config import Settings


class TestEngineKwargsForSqlite:
    """SQLite DATABASE_URL'i ile — pool ayarları YOK SAYILMALI."""

    def test_sqlite_url_emits_check_same_thread(self):
        """SQLite için `connect_args` (`check_same_thread=False`) olmalı."""
        from app import database

        fake_settings = Settings(DATABASE_URL="sqlite:///./test.db", API_DEBUG=False)
        with patch.object(database, "settings", fake_settings):
            kwargs = database._build_engine_kwargs()

        assert kwargs["connect_args"] == {"check_same_thread": False}
        # Pool ayarları YOK olmalı — SQLite tek-bağlantılı
        assert "pool_size" not in kwargs
        assert "max_overflow" not in kwargs
        assert "pool_pre_ping" not in kwargs

    def test_sqlite_memory_url_also_skips_pool(self):
        """`sqlite://` (in-memory) için de pool yok."""
        from app import database

        fake_settings = Settings(DATABASE_URL="sqlite://", API_DEBUG=False)
        with patch.object(database, "settings", fake_settings):
            kwargs = database._build_engine_kwargs()

        assert "pool_size" not in kwargs
        assert kwargs["connect_args"] == {"check_same_thread": False}


class TestEngineKwargsForPostgres:
    """PostgreSQL URL'i ile — settings.DB_POOL_* değerleri kwargs'a yansımalı."""

    def test_postgres_url_applies_default_pool_settings(self):
        """Default pool ayarları (5, 10, True, 3600) kwargs'a geçmeli."""
        from app import database

        fake_settings = Settings(
            DATABASE_URL="postgresql://user:pass@db:5432/sfdap",
            API_DEBUG=False,
        )
        with patch.object(database, "settings", fake_settings):
            kwargs = database._build_engine_kwargs()

        assert kwargs["pool_size"] == 5
        assert kwargs["max_overflow"] == 10
        assert kwargs["pool_pre_ping"] is True
        assert kwargs["pool_recycle"] == 3600
        # SQLite arg'ı OLMAMALI
        assert "connect_args" not in kwargs

    def test_postgres_url_honours_overridden_pool_settings(self):
        """Settings üzerinden override edilen pool değerleri kwargs'a yansır."""
        from app import database

        fake_settings = Settings(
            DATABASE_URL="postgresql://user:pass@db:5432/sfdap",
            DB_POOL_SIZE=20,
            DB_MAX_OVERFLOW=40,
            DB_POOL_PRE_PING=False,
            DB_POOL_RECYCLE=1800,
        )
        with patch.object(database, "settings", fake_settings):
            kwargs = database._build_engine_kwargs()

        assert kwargs["pool_size"] == 20
        assert kwargs["max_overflow"] == 40
        assert kwargs["pool_pre_ping"] is False
        assert kwargs["pool_recycle"] == 1800

    def test_postgresql_short_form_url_also_works(self):
        """`postgresql+psycopg2://` ve `postgres://` prefix'leri de tanınmalı.

        Not: `_build_engine_kwargs` "sqlite ile başlamayan" her şeyi
        server-DB sayar; bu PostgreSQL, MySQL ve daha az yaygın diyalektleri
        kapsar (genel pratik).
        """
        from app import database

        fake_settings = Settings(
            DATABASE_URL="postgresql+psycopg2://user:pass@db:5432/sfdap",
            API_DEBUG=False,
        )
        with patch.object(database, "settings", fake_settings):
            kwargs = database._build_engine_kwargs()

        assert "pool_size" in kwargs


class TestEngineDebugFlag:
    """`echo` (SQL log) flag'i her iki dialect için de uygulanmalı."""

    def test_debug_flag_propagated_for_sqlite(self):
        from app import database

        fake_settings = Settings(DATABASE_URL="sqlite:///./test.db", API_DEBUG=True)
        with patch.object(database, "settings", fake_settings):
            kwargs = database._build_engine_kwargs()

        assert kwargs["echo"] is True

    def test_debug_flag_propagated_for_postgres(self):
        from app import database

        fake_settings = Settings(DATABASE_URL="postgresql://x:y@db/z", API_DEBUG=True)
        with patch.object(database, "settings", fake_settings):
            kwargs = database._build_engine_kwargs()

        assert kwargs["echo"] is True
