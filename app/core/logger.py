"""
SFDAP Logger Configuration
============================
Loguru-based central logger with two output formats:
- `LOG_FORMAT=text` (default): colored console + file rotation
- `LOG_FORMAT=json`: structured single-line JSON for production
  observability stacks

---

Loguru tabanlı central logger; text (renkli console, default) ve json
(structured, production observability) iki formatı destekler.
"""

from __future__ import annotations

import json
import logging
import sys

from loguru import logger

from app.config import settings


class InterceptHandler(logging.Handler):
    """Standart logging mesajlarını yakalayıp Loguru'ya yönlendirir.

    Bu sayede uvicorn, fastapi vb. kütüphanelerin logları tek bir yapıda
    toplanır.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Forward a stdlib `LogRecord` to loguru at the right level."""
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _json_formatter(record: dict) -> str:
    """Structured JSON log line — production observability stack için.

    Her log record'u tek bir JSON satırına çevrilir. trace_id (request_id
    middleware'le bind edilmişse) extras'tan dahil edilir.

    EN: One-line JSON per log record; includes trace_id from contextvars
    when the request_id middleware has bound it.
    """
    payload = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "logger": record["name"],
        "function": record["function"],
        "line": record["line"],
        "message": record["message"],
    }
    # Extras (logger.contextualize(...) ile bind edilmiş alanlar)
    if record["extra"]:
        payload["extra"] = record["extra"]
    # Exception detayları (varsa)
    if record["exception"]:
        payload["exception"] = {
            "type": record["exception"].type.__name__ if record["exception"].type else None,
            "value": str(record["exception"].value) if record["exception"].value else None,
        }
    # JSON tek satır olarak emit; ensure_ascii=False emoji/Türkçe korunur
    return json.dumps(payload, ensure_ascii=False) + "\n"


def setup_logging() -> None:
    """Loguru'yu tüm sistemin ana loglayıcısı olarak yapılandırır.

    Format `LOG_FORMAT` env değişkenine göre seçilir:
    - "json"  → structured JSON, prod observability stack için
    - "text"  → renkli console (default, dev)

    Seviye `LOG_LEVEL` env'den okunur (default INFO). Geçersiz değerde INFO'ya
    düşer ve uyarı yazılır. File handler ayrıca WARNING'in altına inmez —
    üretimde disk tasarrufu (gürültülü INFO log'lar diske düşmesin).
    """
    # Console seviyesini ayrıştır — geçersizse INFO'ya geri dön
    level_name = settings.LOG_LEVEL.upper()
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    console_level = level_name if level_name in valid_levels else "INFO"

    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(getattr(logging, console_level, logging.INFO))

    for name in logging.root.manager.loggerDict:
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    # Standart loguru handler'ını temizle ve yeniden yapılandır
    logger.remove()

    use_json = settings.LOG_FORMAT.lower() == "json"

    if use_json:
        # JSON formatter — production observability için
        logger.add(sys.stdout, format=_json_formatter, level=console_level, colorize=False, serialize=False)
        logger.add(
            "logs/sfdap_{time}.log",
            rotation="10 MB",
            retention="7 days",
            level="WARNING",
            format=_json_formatter,
            colorize=False,
            serialize=False,
        )
    else:
        # Default text — renkli console + sade dosya
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>",
            level=console_level,
        )
        logger.add(
            "logs/sfdap_{time}.log",
            rotation="10 MB",
            retention="7 days",
            level="WARNING",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        )

    if level_name != console_level:
        logger.warning(
            f"LOG_LEVEL='{settings.LOG_LEVEL}' geçersiz; INFO'ya düşürüldü "
            f"(geçerli: DEBUG|INFO|WARNING|ERROR|CRITICAL)."
        )
    logger.info(f"Loguru başarıyla yapılandırıldı (LOG_FORMAT={settings.LOG_FORMAT}, LOG_LEVEL={console_level}).")
