"""
SFDAP Veritabanı Bağlantı Yönetimi
====================================
SQLAlchemy engine, sessionmaker ve dependency-injection için `get_db()` helper.

- Engine `settings.DATABASE_URL` üzerinden yapılandırılır:
  dev → SQLite (`sfdap_dev.db`), prod → PostgreSQL.
- `naming_convention` ile constraint adlandırma standartlaştırılır
  (Alembic auto-generate'in tutarlı isim üretmesi için).
- `init_db()` sadece testlerde / ilk başlangıçta `create_all` ile tabloları
  yaratır; üretimde Alembic migration kullanılmalıdır.

Emirhan Günay — Cycle 3/4 Görevi
"""

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=settings.API_DEBUG,
)

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
