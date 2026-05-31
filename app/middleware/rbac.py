"""
RBAC Helpers (REBUILD Faz 1 / Adım 7)
======================================
4-rol erişim kontrolü için router'lar arası tekrar eden iki pattern:

1. **`scope_to_user(query, user, user_col)`** — list/query endpoint'lerini
   role'e göre kapsamlandırır:
       - `admin` / `overseer` / `developer` → bypass (tüm sistem)
       - `farmer` → `query.filter(user_col == user.id)`

2. **`assert_farm_ownership(db, farm_id, user)`** — detail/write endpoint'ler
   öncesi sahiplik check'i:
       - `admin` / `overseer` / `developer` → bypass
       - `farmer` → kendi çiftliği değilse 403

Helper'lar tüm router'lar (`farms`, `sensors`, `weather`, `irrigation`,
`fertilizer`, `plants`, `alerts`, `analytics`) tarafından kullanılır.

Rol semantik:
    farmer    — kendi farm/field/sensor zinciri (write + read)
    developer — test/integration namespace (geliştirici aracı; prod
                yazılarına dokunamaz, ama read için sistem-geneli)
    overseer  — sistem-geneli read-only (sistem gözetmeni)
    admin     — tüm sistem read + write + kullanıcı yönetimi
"""

from __future__ import annotations

from sqlalchemy.orm import Query, Session

from app.middleware.exceptions import ForbiddenError, NotFoundError
from app.models.models import Farm, Field, Sensor, User

# Bypass set'i — bu rollerin scope filter'ı uygulanmaz, sistem-geneli
# verilere erişim hakları vardır. `developer` ek bir set'e mantıken
# girebilir ama Faz 1'de "geliştirici tüm sistemi görebilir" basit
# semantiği yeterli.
_BYPASS_ROLES = frozenset({"admin", "overseer", "developer"})

# Yazma yetkisi olan roller. `farmer` kendi kaynağına yazar; `admin`
# sistem-geneli yazar. `developer` ve `overseer` write yapamaz (sırasıyla
# read-only ve test-namespace).
_WRITE_ROLES = frozenset({"admin", "farmer"})


def scope_to_user(query: Query, user: User, user_col) -> Query:  # noqa: ANN001
    """List query'sini rol'e göre kapsamlandır.

    Args:
        query: SQLAlchemy `Query` instance (örn. `db.query(Farm)`)
        user: `_get_current_user`'dan gelen `User` ORM nesnesi
        user_col: scope için kullanılacak FK kolonu
                  (örn. `Farm.user_id`, `Field.farm_id` değil!)

    Returns:
        Filtreli query. `farmer` ise `user_col == user.id` eklenir;
        admin/overseer/developer için query değişmeden döner.
    """
    if user.role in _BYPASS_ROLES:
        return query
    return query.filter(user_col == user.id)


def assert_farm_ownership(db: Session, farm_id: int, user: User) -> None:
    """Detail/write endpoint öncesi `Farm` sahipliğini doğrula.

    Args:
        db: SQLAlchemy session
        farm_id: kontrol edilecek `Farm.id`
        user: caller `User` ORM nesnesi

    Raises:
        ForbiddenError (403): farmer ise ve sahibi değilse
        NotFoundError (404): farm hiç mevcut değilse (admin için bile)

    Bypass:
        admin/overseer/developer için sadece varlık check'i yapılır;
        sahiplik doğrulanmaz.
    """
    farm = db.query(Farm.id, Farm.user_id).filter(Farm.id == farm_id).first()
    if farm is None:
        raise NotFoundError("Çiftlik")
    if user.role in _BYPASS_ROLES:
        return
    if farm.user_id != user.id:
        raise ForbiddenError(detail="Bu çiftliğe erişim yetkin yok.")


def is_write_allowed(user: User) -> bool:
    """Caller'ın yazma yetkisi var mı? (overseer/developer için False)."""
    return user.role in _WRITE_ROLES


def require_write(user: User) -> None:
    """Yazma yetkisi yoksa 403 fırlat (overseer/developer read-only).

    `is_write_allowed`'un raise eden versiyonu; router'lardaki yinelenen
    `_require_write` helper'larının tek kaynağı.
    """
    if user.role not in _WRITE_ROLES:
        raise ForbiddenError(detail=f"Yazma yetkisi yok (rol: {user.role}); farmer veya admin gerek.")


def assert_field_ownership(db: Session, field_id: int, user: User) -> None:
    """`Field` sahipliğini Field → Farm → user_id zinciri ile doğrula.

    Raises:
        ForbiddenError (403): farmer ise ve sahibi değilse
        NotFoundError (404): field hiç mevcut değilse
    """
    row = db.query(Field.id, Farm.user_id).join(Farm, Field.farm_id == Farm.id).filter(Field.id == field_id).first()
    if row is None:
        raise NotFoundError("Tarla")
    if user.role in _BYPASS_ROLES:
        return
    if row.user_id != user.id:
        raise ForbiddenError(detail="Bu tarlaya erişim yetkin yok.")


def assert_sensor_ownership(db: Session, sensor_id: int, user: User) -> None:
    """`Sensor` sahipliğini Sensor → Field → Farm → user_id zinciri ile doğrula.

    Raises:
        ForbiddenError (403): farmer ise ve sahibi değilse
        NotFoundError (404): sensor hiç mevcut değilse
    """
    row = (
        db.query(Sensor.id, Farm.user_id)
        .join(Field, Sensor.field_id == Field.id)
        .join(Farm, Field.farm_id == Farm.id)
        .filter(Sensor.id == sensor_id)
        .first()
    )
    if row is None:
        raise NotFoundError("Sensör")
    if user.role in _BYPASS_ROLES:
        return
    if row.user_id != user.id:
        raise ForbiddenError(detail="Bu sensöre erişim yetkin yok.")


def scope_sensors_to_user(query: Query, user: User) -> Query:
    """Sensor list query'sini rol'e göre kapsamlandır (Sensor → Field → Farm join)."""
    if user.role in _BYPASS_ROLES:
        return query
    return (
        query.join(Field, Sensor.field_id == Field.id)
        .join(Farm, Field.farm_id == Farm.id)
        .filter(Farm.user_id == user.id)
    )
