"""
SFDAP Database Connection Management
======================================
SQLAlchemy engine, sessionmaker, and `get_db()` dependency-injection helper.

- Engine is configured from `settings.DATABASE_URL`:
  dev → SQLite (`sfdap_dev.db`), prod → PostgreSQL.
- **Connection pool tuning**: for PostgreSQL/MySQL, `pool_size`,
  `max_overflow`, `pool_pre_ping`, `pool_recycle` are read from env.
  SQLite is single-connection so these settings are ignored.
- `naming_convention` standardizes constraint names (so Alembic
  autogenerate emits consistent identifiers).
- `init_db()` is only for tests / first boot via `create_all`; production
  must use Alembic migrations.

---

SQLAlchemy engine, sessionmaker ve `get_db()` dependency helper.
Dev'de SQLite, production'da PostgreSQL/MySQL kullanılır; pool ayarları
sadece server DB'lerde aktif, SQLite'ta no-op. Constraint naming
standartlaştırılır, init_db sadece test/ilk boot içindir.
"""

from collections.abc import Iterator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings

# SQLite INTEGER is 64-bit signed; unbounded int path/query params can
# overflow the binding and surface as a 500. Cap at 2**63 - 1.
# ---
# SQLite INTEGER 64-bit signed; sınırsız int path/query parametreleri
# binding'de overflow olur ve 500 döner. Routerlar bu sabitle sınırlamalı.
MAX_SQLITE_INT = 9_223_372_036_854_775_807  # 2**63 - 1


def _build_engine_kwargs() -> dict:
    """`DATABASE_URL`'e bakarak uygun engine argümanlarını üretir.

    SQLite: `check_same_thread=False` (FastAPI multi-thread için)
    PostgreSQL/MySQL: pool_size, max_overflow, pool_pre_ping, pool_recycle

    EN: Returns the right kwargs for the active DB dialect; SQLite gets
    multi-thread arg, server DBs get pool tuning.
    """
    is_sqlite = settings.DATABASE_URL.startswith("sqlite")
    # echo prod'da ZORLA kapalı: SQLAlchemy echo tüm SQL + parametreleri (şifre
    # hash, PII) log'a yazar. API_DEBUG yanlışlıkla True bırakılsa bile prod'da
    # sızıntı olmaz (audit YÜKSEK).
    kwargs: dict = {"echo": settings.API_DEBUG and settings.ENVIRONMENT != "production"}

    if is_sqlite:
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # Prod-grade pool ayarları (env-driven, settings tarafında default
        # değerleri var; .env üzerinden override edilebilir).
        kwargs["pool_size"] = settings.DB_POOL_SIZE
        kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
        kwargs["pool_pre_ping"] = settings.DB_POOL_PRE_PING
        kwargs["pool_recycle"] = settings.DB_POOL_RECYCLE
        # AUDIT L7: PostgreSQL oturum saat dilimini UTC'ye sabitle. Modelde naive
        # DateTime kolonları (TIMESTAMP WITHOUT TIME ZONE) var; filtreler ise UTC-aware
        # (datetime.now(UTC)). Oturum TZ'i UTC olmayınca karşılaştırma sunucu saatine
        # göre kayabilir → UTC'ye sabitlemek naive-kolon/aware-filtre tutarlılığını
        # garanti eder (timestamptz kolonlara geçiş = ayrı migration, follow-up).
        kwargs["connect_args"] = {"options": "-c timezone=utc"}
    return kwargs


engine = create_engine(settings.DATABASE_URL, **_build_engine_kwargs())

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
metadata = MetaData(naming_convention=naming_convention)
Base = declarative_base(metadata=metadata)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
