"""Add note to holdings

Revision ID: d4a8e5f1c2b9
Revises: b1c2d3e4f5a6
Create Date: 2026-05-03 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4a8e5f1c2b9"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("holdings", sa.Column("note", sa.String(length=2000), nullable=True))


def downgrade() -> None:
    op.drop_column("holdings", "note")
