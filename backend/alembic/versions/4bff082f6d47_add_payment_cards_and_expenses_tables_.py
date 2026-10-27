"""add payment_cards and expenses tables, enable pgcrypto

Revision ID: 4bff082f6d47
Revises: 41caac9563f9
Create Date: 2026-10-24 11:06:28.579827

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4bff082f6d47'
down_revision: Union[str, None] = '41caac9563f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # payment_cards.card_number_encrypted is pgp_sym_encrypt() output -
    # the extension that function lives in, not installed by default.
    #
    # This migration deliberately does NOT create payment_cards or
    # expenses itself. Both are brand-new tables already declared on
    # Base.metadata (models.py), and app.database.init_db()'s
    # create_all() - which still runs on every startup, right after
    # this migration, exactly as it always has - creates any table that
    # doesn't exist yet, indexes included (both tables use index=True
    # on the relevant columns). Giving this migration its own
    # op.create_table for the same tables would make the two collide:
    # whichever one runs second hits "relation already exists". Only
    # CREATE EXTENSION has no create_all() equivalent, so that is all
    # that belongs here.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")


def downgrade() -> None:
    # No DROP TABLE here to pair with upgrade()'s lack of CREATE TABLE -
    # downgrading past this revision is not a supported path once data
    # exists in either table; drop them by hand first if that's truly
    # the intent. Dropping the extension is left alone too: another
    # migration may come to depend on pgcrypto later, and DROP EXTENSION
    # would fail loudly anyway if anything still uses it.
    pass
