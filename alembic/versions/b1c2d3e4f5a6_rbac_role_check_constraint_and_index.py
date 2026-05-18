"""rbac: role CHECK constraint + index + backfill (REBUILD Faz 1 / Adım 2)

Revision ID: b1c2d3e4f5a6
Revises: 4d1a1503f306
Create Date: 2026-05-18 09:00:00.000000

REBUILD Faz 1 — 4-rol RBAC için DB-side koruma:

1. Backfill: `users.role` NULL veya '' olan satırları 'farmer' yap.
2. CHECK constraint: `role IN ('farmer','developer','overseer','admin')`
   — SQLite batch_alter_table ile tablo rebuild edilerek eklenir.
3. Index: `ix_users_role` — farmer/admin scope filter'larında full-scan
   önler.

Bu migration idempotent değildir (constraint adı sabit); downgrade
constraint + index'i kaldırır, role değerlerini elle restore etmez.
"""

from collections.abc import Sequence

import sqlalchemy as sa  # noqa: F401 — Alembic style; future ops için import

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: str | Sequence[str] | None = "4d1a1503f306"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Hardcoded — models.py'daki USER_ROLES ile eşleşmek zorunda.
# Migration dosyaları runtime'da app/models import etmez (Alembic env.py
# Base.metadata'yı yükler ama migration body'si bağımsız çalışır).
_ROLES = ("farmer", "developer", "overseer", "admin")
_CHECK_NAME = "ck_users_role_valid"
_INDEX_NAME = "ix_users_role"


def upgrade() -> None:
    """Backfill + CHECK constraint + index."""
    # 1. Backfill: NULL veya boş role değerlerini 'farmer'a çek.
    op.execute("UPDATE users SET role = 'farmer' WHERE role IS NULL OR role = ''")

    # 2. CHECK constraint — SQLite uyumluluğu için batch_alter_table.
    # PostgreSQL native CHECK destekler; SQLite batch tablo rebuild yapar.
    quoted_values = ", ".join(f"'{r}'" for r in _ROLES)
    with op.batch_alter_table("users") as batch_op:
        batch_op.create_check_constraint(
            _CHECK_NAME,
            f"role IN ({quoted_values})",
        )

    # 3. Index — farmer scope filter'ları sık çalışacak.
    op.create_index(_INDEX_NAME, "users", ["role"], unique=False)


def downgrade() -> None:
    """Index + CHECK constraint'i kaldır. role değerleri olduğu gibi kalır."""
    op.drop_index(_INDEX_NAME, table_name="users")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint(_CHECK_NAME, type_="check")
