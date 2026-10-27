"""Standalone bot review grants and idempotent receipt submissions.

Revision ID: 9e21b0d7c4a1
Revises: 4bff082f6d47
"""
from alembic import op
import sqlalchemy as sa

revision = "9e21b0d7c4a1"
down_revision = "4bff082f6d47"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payment_requests", sa.Column("client_request_key", sa.String(100), nullable=True))
    op.add_column("payment_requests", sa.Column("receipt_kind", sa.String(20), nullable=True))
    op.create_unique_constraint("uq_payment_requests_client_key", "payment_requests", ["client_request_key"])
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("standalone_bot_admins"):
        op.create_table(
            "standalone_bot_admins",
            sa.Column("telegram_user_id", sa.BigInteger(), primary_key=True),
            sa.Column("granted_by_telegram_id", sa.BigInteger(), nullable=False),
            sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        )
    else:
        # init_db/create_all can create new ORM tables ahead of Alembic.
        # Preserve existing grants, accepting only the expected structure.
        cols = {c["name"]: c for c in inspector.get_columns("standalone_bot_admins")}
        if (set(cols) != {"telegram_user_id", "granted_by_telegram_id", "granted_at"}
                or inspector.get_pk_constraint("standalone_bot_admins")["constrained_columns"] != ["telegram_user_id"]
                or any(c["nullable"] for c in cols.values())
                or any(not isinstance(cols[k]["type"], sa.BigInteger) for k in ("telegram_user_id", "granted_by_telegram_id"))
                or not getattr(cols["granted_at"]["type"], "timezone", False)):
            raise RuntimeError("Existing standalone_bot_admins schema is incompatible")


def downgrade() -> None:
    op.drop_table("standalone_bot_admins")
    op.drop_constraint("uq_payment_requests_client_key", "payment_requests", type_="unique")
    op.drop_column("payment_requests", "receipt_kind")
    op.drop_column("payment_requests", "client_request_key")
