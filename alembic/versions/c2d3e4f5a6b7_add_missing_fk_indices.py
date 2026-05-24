"""v3-5: add missing FK indices on farms.user_id, fields.farm_id, fields.crop_id

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-05-24

RBAC ownership filtreleri (Farm.user_id == user.id) ve çiftliğin tarlaları
join'leri (Field.farm_id == farm_id) sık erişilir. Bu FK kolonlarına
explicit index eklemek, çoklu çiftlik/tarla senaryosunda lookup'ı O(log n)
yapar. crop_id index'i analytics join performansı için.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: str | Sequence[str] | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add three missing FK indices for query performance."""
    op.create_index("ix_farms_user_id", "farms", ["user_id"])
    op.create_index("ix_fields_farm_id", "fields", ["farm_id"])
    op.create_index("ix_fields_crop_id", "fields", ["crop_id"])


def downgrade() -> None:
    """Drop the indices added in upgrade()."""
    op.drop_index("ix_fields_crop_id", table_name="fields")
    op.drop_index("ix_fields_farm_id", table_name="fields")
    op.drop_index("ix_farms_user_id", table_name="farms")
