from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.database import get_db
from app.models.models import Farm
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
