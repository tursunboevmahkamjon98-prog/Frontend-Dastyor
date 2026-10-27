"""add users.admin_tier with role-admin check constraint

Revision ID: 6084e6741bb1
Revises: c848a5a360d1
Create Date: 2026-10-24 10:34:58.217270

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6084e6741bb1'
down_revision: Union[str, None] = 'c848a5a360d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("admin_tier", sa.String(20), nullable=True))
    # Keeps the two columns from drifting apart: a tier only ever means
    # something next to role == 'admin'. NULL admin_tier is still valid
    # for an admin (see models.py's comment — it means "pre-tier admin,
    # treat as super"), this only forbids a NON-admin from having a tier.
    op.create_check_constraint(
        "ck_users_admin_tier_requires_admin_role",
        "users",
        "admin_tier IS NULL OR role = 'admin'",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_admin_tier_requires_admin_role", "users", type_="check")
    op.drop_column("users", "admin_tier")
