"""The enum for account_type now includes '特定' (meaning 'Specific') along with the other account types.

Revision ID: efe971be2748
Revises: a86e14099dc8
Create Date: 2025-03-19 20:58:15.523252

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'efe971be2748'
down_revision: Union[str, None] = 'a86e14099dc8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE account_types ADD VALUE '特定' AFTER 'NISA(成長投資枠)'")


def downgrade() -> None:
    pass
