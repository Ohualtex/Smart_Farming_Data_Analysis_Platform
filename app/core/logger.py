"""
SFDAP Logger Configuration
============================
Loguru tabanlı central logger.

İki çıktı formatı (shiftFinal — Mehmet A2):
- `LOG_FORMAT=text` (default): Renkli console + dosya rotation
- `LOG_FORMAT=json`: Structured JSON (production observability stack)

EN: Loguru-based central logger with two output formats — text (colored
console, default) and JSON (structured, production stack compatible).
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
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _json_formatter(record) -> str:
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
    """
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(logging.INFO)

    for name in logging.root.manager.loggerDict:
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    # Standart loguru handler'ını temizle ve yeniden yapılandır
    logger.remove()

    use_json = settings.LOG_FORMAT.lower() == "json"

    if use_json:
        # JSON formatter — production observability için
        logger.add(sys.stdout, format=_json_formatter, level="INFO", colorize=False, serialize=False)
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
            level="INFO",
        )
        logger.add(
            "logs/sfdap_{time}.log",
            rotation="10 MB",
            retention="7 days",
            level="WARNING",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        )

    logger.info(f"Loguru basariyla yapilandirildi (LOG_FORMAT={settings.LOG_FORMAT})!")
