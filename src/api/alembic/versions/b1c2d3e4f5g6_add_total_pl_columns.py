"""add total_pl and total_pl_percentage columns

Revision ID: b1c2d3e4f5g6
Revises: a1b2c3d4e5f6
Create Date: 2026-01-29 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5g6"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # holdingsテーブルにtotal_pl, total_pl_percentageカラムを追加
    op.add_column("holdings", sa.Column("total_pl", sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column(
        "holdings", sa.Column("total_pl_percentage", sa.Numeric(precision=5, scale=2), nullable=True)
    )

    # portfolio_historyテーブルにtotal_pl, total_pl_percentageカラムを追加
    op.add_column(
        "portfolio_history",
        sa.Column("total_pl", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
    )
    op.add_column(
        "portfolio_history",
        sa.Column(
            "total_pl_percentage", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0"
        ),
    )


def downgrade() -> None:
    # portfolio_historyテーブルからtotal_pl, total_pl_percentageカラムを削除
    op.drop_column("portfolio_history", "total_pl_percentage")
    op.drop_column("portfolio_history", "total_pl")

    # holdingsテーブルからtotal_pl, total_pl_percentageカラムを削除
    op.drop_column("holdings", "total_pl_percentage")
    op.drop_column("holdings", "total_pl")
