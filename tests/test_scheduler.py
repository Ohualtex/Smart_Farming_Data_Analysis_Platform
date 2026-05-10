"""
APScheduler Arka Plan Görev Testleri
======================================
`app/tasks/scheduler.py` lifecycle (start/shutdown) ve async fetch
görevini gerçek scheduler/broker olmadan mock'larla test eder.

EN: Tests for APScheduler lifecycle and the async daily weather fetch
job — fully mocked, no real scheduler or external API.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.models import Farm, User
from app.tasks import scheduler as scheduler_module

# ─── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def farms_setup(db):
    """User → Farm zinciri (1 lokasyonlu, 1 lokasyonsuz)."""
    user = User(
        name="Sched Test",
        email="sched@x.com",
        role="farmer",
        password_hash="dummy$hash",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    located = Farm(
        user_id=user.id,
        name="Located Farm",
        city="Ankara",
        region="Ic Anadolu",
        location_lat=40.0,
        location_lng=33.0,
    )
    no_loc = Farm(
        user_id=user.id,
        name="No Location Farm",
        city="Test",
        region="Test",
    )
    db.add_all([located, no_loc])
    db.commit()
    return [located, no_loc]


# ─── Lifecycle (start / shutdown) ─────────────────────────────────────


class TestStartScheduler:
    """`start_scheduler()` add_job + start davranışı."""

    def test_adds_jobs_and_starts_when_not_running(self, monkeypatch):
        mock_scheduler = MagicMock()
        mock_scheduler.running = False
        monkeypatch.setattr(scheduler_module, "scheduler", mock_scheduler)

        scheduler_module.start_scheduler()

        # 2 job eklenmeli: fetch_daily_weather + archive_old_sensor_readings
        assert mock_scheduler.add_job.call_count == 2
        registered_ids = {call.kwargs["id"] for call in mock_scheduler.add_job.call_args_list}
        assert registered_ids == {"fetch_daily_weather", "archive_old_sensor_readings"}
        # Tüm job'lar replace_existing=True ile eklenmeli
        for call in mock_scheduler.add_job.call_args_list:
            assert call.kwargs["replace_existing"] is True
        mock_scheduler.start.assert_called_once()

    def test_skips_start_if_already_running(self, monkeypatch):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        monkeypatch.setattr(scheduler_module, "scheduler", mock_scheduler)

        scheduler_module.start_scheduler()

        # add_job hâlâ çağrılır (replace_existing) ama start çağrılmaz
        assert mock_scheduler.add_job.call_count == 2
        mock_scheduler.start.assert_not_called()


class TestArchiveJob:
    """`archive_old_sensor_readings_job` wrapper davranışı."""

    def test_calls_archive_old_readings_with_session(self, db, monkeypatch):
        """Job test session ile archive_old_readings'i çağırmalı."""

        called_with = {}

        def fake_archive(session, cutoff_days=30):
            called_with["session"] = session
            from datetime import UTC, datetime, timedelta

            from app.services.sensor_archiver import ArchiveResult

            return ArchiveResult(
                aggregates_written=0,
                readings_deleted=0,
                cutoff=datetime.now(UTC) - timedelta(days=cutoff_days),
            )

        # scheduler modülündeki referansı override et (sensor_archiver'dan import edilmiş)
        monkeypatch.setattr(scheduler_module, "archive_old_readings", fake_archive)
        monkeypatch.setattr(scheduler_module, "get_db", lambda: iter([db]))

        scheduler_module.archive_old_sensor_readings_job()
        assert called_with["session"] is db

    def test_swallows_exception_and_closes_db(self, monkeypatch):
        """Archive hata atsa job exception fırlatmamalı, db.close() yine çağrılmalı."""
        bad_db = MagicMock()

        def fake_archive(_session, cutoff_days=30):
            raise RuntimeError("DB unreachable")

        monkeypatch.setattr(scheduler_module, "archive_old_readings", fake_archive)
        monkeypatch.setattr(scheduler_module, "get_db", lambda: iter([bad_db]))

        # Exception sessizce yakalanır
        scheduler_module.archive_old_sensor_readings_job()
        bad_db.close.assert_called_once()


class TestShutdownScheduler:
    """`shutdown_scheduler()` davranışı."""

    def test_shuts_down_when_running(self, monkeypatch):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        monkeypatch.setattr(scheduler_module, "scheduler", mock_scheduler)

        scheduler_module.shutdown_scheduler()

        mock_scheduler.shutdown.assert_called_once()

    def test_noop_when_not_running(self, monkeypatch):
        mock_scheduler = MagicMock()
        mock_scheduler.running = False
        monkeypatch.setattr(scheduler_module, "scheduler", mock_scheduler)

        scheduler_module.shutdown_scheduler()

        mock_scheduler.shutdown.assert_not_called()


# ─── Async fetch görevi ───────────────────────────────────────────────


class TestFetchDailyWeather:
    """`fetch_daily_weather_for_all_farms` async iş akışı."""

    def test_skips_farms_without_location(self, db, farms_setup, monkeypatch):
        """Lokasyonu olmayan çiftlik için fetch çağrılmamalı."""
        mock_ws = MagicMock()
        mock_ws.fetch_current_weather = AsyncMock(return_value={"temperature_c": 20.0})
        mock_ws.clean_weather_data = MagicMock(return_value={"temperature_c": 20.0})
        mock_ws.save_weather_record = MagicMock()

        monkeypatch.setattr(scheduler_module, "WeatherService", lambda: mock_ws)
        # get_db test session'ını döndürsün
        monkeypatch.setattr(scheduler_module, "get_db", lambda: iter([db]))

        asyncio.run(scheduler_module.fetch_daily_weather_for_all_farms())

        # 2 farm var — sadece lokasyonlusu için fetch çağrılmalı
        assert mock_ws.fetch_current_weather.call_count == 1
        mock_ws.save_weather_record.assert_called_once()

    def test_continues_when_one_farm_fails(self, db, farms_setup, monkeypatch):
        """Bir çiftlik için fetch hata atsa diğer çiftlik(ler) için akış devam etmeli."""
        # 3. farm ekle (ikinci lokasyonlu)
        user = db.query(User).first()
        farms_setup.append(
            Farm(
                user_id=user.id,
                name="Other Located Farm",
                city="Izmir",
                region="Ege",
                location_lat=38.4,
                location_lng=27.1,
            )
        )
        db.add(farms_setup[-1])
        db.commit()

        mock_ws = MagicMock()
        # İlk çağrı patlar, ikinci başarılı
        mock_ws.fetch_current_weather = AsyncMock(side_effect=[RuntimeError("API down"), {"temperature_c": 22.0}])
        mock_ws.clean_weather_data = MagicMock(return_value={"temperature_c": 22.0})
        mock_ws.save_weather_record = MagicMock()

        monkeypatch.setattr(scheduler_module, "WeatherService", lambda: mock_ws)
        monkeypatch.setattr(scheduler_module, "get_db", lambda: iter([db]))

        asyncio.run(scheduler_module.fetch_daily_weather_for_all_farms())

        # 2 lokasyonlu farm → 2 kez fetch denenmeli, 1 kez save edilmeli
        assert mock_ws.fetch_current_weather.call_count == 2
        assert mock_ws.save_weather_record.call_count == 1

    def test_handles_outer_exception_gracefully(self, db, monkeypatch):
        """db.query() patlasa fonksiyon exception fırlatmamalı."""
        bad_db = MagicMock()
        bad_db.query.side_effect = RuntimeError("DB connection lost")
        bad_db.close = MagicMock()

        monkeypatch.setattr(scheduler_module, "get_db", lambda: iter([bad_db]))
        monkeypatch.setattr(scheduler_module, "WeatherService", lambda: MagicMock())

        # Beklenen: exception sessizce yakalanır, db.close() yine çağrılır
        asyncio.run(scheduler_module.fetch_daily_weather_for_all_farms())
        bad_db.close.assert_called_once()
