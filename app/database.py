"""
SFDAP Veritabanı Bağlantı Yönetimi
====================================
SQLAlchemy engine, sessionmaker ve dependency-injection için `get_db()` helper.

- Engine `settings.DATABASE_URL` üzerinden yapılandırılır:
  dev → SQLite (`sfdap_dev.db`), prod → PostgreSQL.
- **Connection pool tuning** (shiftFinal — Emirhan A4): PostgreSQL/MySQL
  için `pool_size`, `max_overflow`, `pool_pre_ping`, `pool_recycle`
  env'lerden okunur. SQLite tek-bağlantılı olduğu için bu ayarlar yok
  sayılır.
- `naming_convention` ile constraint adlandırma standartlaştırılır
  (Alembic auto-generate'in tutarlı isim üretmesi için).
- `init_db()` sadece testlerde / ilk başlangıçta `create_all` ile tabloları
  yaratır; üretimde Alembic migration kullanılmalıdır.

Emirhan Günay — Cycle 3/4 + shiftFinal A4 Görevi

EN: Engine config with environment-driven pool tuning for PostgreSQL/
MySQL (no-op on SQLite). pool_pre_ping defends against killed connections
in long-running deployments; pool_recycle prevents idle-disconnect.
"""

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


def _build_engine_kwargs() -> dict:
    """`DATABASE_URL`'e bakarak uygun engine argümanlarını üretir.

    SQLite: `check_same_thread=False` (FastAPI multi-thread için)
    PostgreSQL/MySQL: pool_size, max_overflow, pool_pre_ping, pool_recycle

    EN: Returns the right kwargs for the active DB dialect; SQLite gets
    multi-thread arg, server DBs get pool tuning.
    """
    is_sqlite = settings.DATABASE_URL.startswith("sqlite")
    kwargs: dict = {"echo": settings.API_DEBUG}

    if is_sqlite:
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # Prod-grade pool ayarları (env-driven, settings tarafında default
        # değerleri var; .env üzerinden override edilebilir).
        kwargs["pool_size"] = settings.DB_POOL_SIZE
        kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
        kwargs["pool_pre_ping"] = settings.DB_POOL_PRE_PING
        kwargs["pool_recycle"] = settings.DB_POOL_RECYCLE
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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
