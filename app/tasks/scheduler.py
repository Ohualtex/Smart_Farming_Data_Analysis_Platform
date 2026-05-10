from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.database import get_db
from app.models.models import Farm
from app.services.sensor_archiver import archive_old_readings
from app.services.weather_service import WeatherService

scheduler = AsyncIOScheduler()


async def fetch_daily_weather_for_all_farms() -> None:
    """
    Her çiftlik için günlük hava durumu verilerini çekip veritabanına kaydeden arka plan görevi.

    Akış: WeatherService.fetch_current_weather (async API) → clean_weather_data →
    save_weather_record. Tek bir çiftlikte hata olsa bile diğerleri devam eder.
    """
    logger.info("Gunluk hava durumu verisi cekme gorevi basliyor...")
    db = next(get_db())
    try:
        farms = db.query(Farm).all()
        weather_service = WeatherService()

        for farm in farms:
            if not (farm.location_lat and farm.location_lng):
                logger.warning(f"Ciftlik {farm.id} icin lokasyon verisi eksik, hava durumu atlandi.")
                continue
            try:
                raw = await weather_service.fetch_current_weather(farm.location_lat, farm.location_lng)
                cleaned = weather_service.clean_weather_data(raw)
                weather_service.save_weather_record(db, farm.id, cleaned)
                logger.info(f"Ciftlik {farm.id} ({farm.name}) icin hava durumu kaydedildi.")
            except Exception:
                logger.exception(f"Ciftlik {farm.id} icin hava durumu cekilemedi")

        logger.info("Gunluk hava durumu verisi cekme gorevi tamamlandi.")
    except Exception:
        logger.exception("Hava durumu gorevinde beklenmeyen hata")
    finally:
        db.close()


def archive_old_sensor_readings_job() -> None:
    """30 günden eski sensör okumalarını aylık özete taşıyan haftalık görev.

    EN: Weekly job archiving sensor readings older than 30 days into the
    monthly aggregate table; senkron, scheduler ile uyumlu olması için
    `next(get_db())` kullanır.
    """
    logger.info("Sensor okumalari arsivleme gorevi basliyor...")
    db = next(get_db())
    try:
        result = archive_old_readings(db)
        logger.info(
            f"Sensor arsivleme tamamlandi: {result.aggregates_written} aggregate, "
            f"{result.readings_deleted} ham kayit (cutoff={result.cutoff.isoformat()})"
        )
    except Exception:
        logger.exception("Sensor arsivleme gorevinde beklenmeyen hata")
    finally:
        db.close()


def start_scheduler() -> None:
    """APScheduler'ı yapılandırır ve başlatır."""
    # Her gece saat 02:00'de çalışacak şekilde ayarla
    scheduler.add_job(
        fetch_daily_weather_for_all_farms,
        trigger=CronTrigger(hour=2, minute=0),
        id="fetch_daily_weather",
        name="Gunluk Hava Durumu Cekimi",
        replace_existing=True,
    )
    # Her Pazar 03:30'da sensör okumaları arşivleme — hava durumundan 1.5 saat sonra
    scheduler.add_job(
        archive_old_sensor_readings_job,
        trigger=CronTrigger(day_of_week="sun", hour=3, minute=30),
        id="archive_old_sensor_readings",
        name="Sensor Okumalari Haftalik Arsivleme",
        replace_existing=True,
    )
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler baslatildi ve gorevler eklendi.")
    else:
        logger.info("APScheduler zaten calisiyor.")


def shutdown_scheduler() -> None:
    """APScheduler'ı güvenli bir şekilde kapatır."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler kapatildi.")
    else:
        logger.info("APScheduler zaten kapali.")
