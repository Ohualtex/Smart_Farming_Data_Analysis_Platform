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
    """
    logger.info("Gunluk hava durumu verisi cekme gorevi basliyor...")
    try:
        db = next(get_db())
        farms = db.query(Farm).all()
        weather_service = WeatherService()

        for farm in farms:
            if farm.location_lat and farm.location_lng:
                try:
                    weather_service.fetch_and_store_weather(db, farm.id, farm.location_lat, farm.location_lng)
                    logger.info(f"Ciftlik {farm.id} ({farm.name}) icin hava durumu kaydedildi.")
                except Exception as e:
                    logger.error(f"Ciftlik {farm.id} icin hava durumu cekilemedi: {str(e)}")
            else:
                logger.warning(f"Ciftlik {farm.id} icin lokasyon verisi eksik, hava durumu atlandi.")

        logger.info("Gunluk hava durumu verisi cekme gorevi tamamlandi.")
    except Exception as e:
        logger.exception(f"Hava durumu gorevinde beklenmeyen hata: {str(e)}")


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
