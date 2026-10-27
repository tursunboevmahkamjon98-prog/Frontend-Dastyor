"""add telegram_admins.reviewed_at for the migration-review worklist

Revision ID: 41caac9563f9
Revises: 6084e6741bb1
Create Date: 2026-10-24 10:53:27.986918

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '41caac9563f9'
down_revision: Union[str, None] = '6084e6741bb1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "telegram_admins",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("telegram_admins", "reviewed_at")
