"""add usd price fields to holdings

Revision ID: 7b1c2d3e4f5a
Revises: 55023a6af252
Create Date: 2026-05-20 00:00:00.000000

"""

from typing import Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7b1c2d3e4f5a"
down_revision: Union[str, None] = "55023a6af252"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("holdings", sa.Column("current_price_usd", sa.Float(), nullable=True))
    op.add_column("holdings", sa.Column("market_value_usd", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("holdings", "market_value_usd")
    op.drop_column("holdings", "current_price_usd")
