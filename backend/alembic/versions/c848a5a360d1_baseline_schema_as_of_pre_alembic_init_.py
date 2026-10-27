"""baseline: schema as of pre-alembic init_db state

Revision ID: c848a5a360d1
Revises: 
Create Date: 2026-10-24 10:21:04.794528

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c848a5a360d1'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Deliberately empty. Every table/column this schema already has was
    # created by app.database.init_db() (create_all + hand-written
    # ALTER TABLE ... IF NOT EXISTS statements), which keeps running
    # unchanged. This revision exists only so app.db_bootstrap can stamp
    # an existing database at "head" without Alembic trying to re-create
    # tables that are already there. Real schema changes start at the
    # next revision.
    pass


def downgrade() -> None:
    pass
