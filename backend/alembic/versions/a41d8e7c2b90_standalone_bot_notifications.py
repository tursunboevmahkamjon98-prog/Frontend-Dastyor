"""Track delivery of standalone bot payment decisions.

Revision ID: a41d8e7c2b90
Revises: 9e21b0d7c4a1
"""
from alembic import op
import sqlalchemy as sa

revision = "a41d8e7c2b90"
down_revision = "9e21b0d7c4a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payment_requests", sa.Column(
        "standalone_notification_sent_at", sa.DateTime(timezone=True),
        nullable=True))


def downgrade() -> None:
    op.drop_column("payment_requests", "standalone_notification_sent_at")
