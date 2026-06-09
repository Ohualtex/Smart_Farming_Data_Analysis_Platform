"""rbac role NOT NULL drift fix (audit ORTA 18)

Revision ID: c5eee337bec4
Revises: c2d3e4f5a6b7
Create Date: 2026-06-09 13:58:12.980002

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5eee337bec4"
down_revision: str | Sequence[str] | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """users.role NOT NULL — model (nullable=False) ile hizala.

    İlk migration role'ü nullable kurmuştu (audit ORTA #18: model/migration
    drift; CHECK constraint NULL'ı reddetmiyordu). Önce NULL/boş role'leri
    'farmer'a backfill et, sonra kolonu NOT NULL yap. PostgreSQL'de native
    ALTER; SQLite'ta batch tablo rebuild (mevcut CHECK + index korunur).
    """
    op.execute("UPDATE users SET role = 'farmer' WHERE role IS NULL OR role = ''")
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("role", existing_type=sa.String(length=20), nullable=False)


def downgrade() -> None:
    """role'ü tekrar nullable yap (drift'in eski hâline dönüş)."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("role", existing_type=sa.String(length=20), nullable=True)
