"""add total_pl columns

Revision ID: c1d2e3f4a5b6
Revises: a1b2c3d4e5f6
Create Date: 2026-01-28 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # holdings テーブルに total_pl カラム追加
    op.add_column("holdings", sa.Column("total_pl", sa.Numeric(precision=10, scale=2), nullable=True))

    # portfolio_history テーブルに total_pl カラム追加
    op.add_column(
        "portfolio_history", sa.Column("total_pl", sa.Numeric(precision=10, scale=2), nullable=True)
    )

    # 既存データの移行: portfolio_history の total_pl を旧 total_unrealized_pl の値にコピー
    # 旧 total_unrealized_pl には 含み損益 + 実現損益 + 配当 が含まれていた
    op.execute(
        """
        UPDATE portfolio_history
        SET total_pl = total_unrealized_pl
    """
    )

    # 旧 total_unrealized_pl を正しい含み損益（時価 - 取得価額）に再計算
    op.execute(
        """
        UPDATE portfolio_history
        SET total_unrealized_pl = total_market_value - total_cost
    """
    )

    # total_pl を NOT NULL に変更
    op.alter_column("portfolio_history", "total_pl", nullable=False)


def downgrade() -> None:
    # 逆移行: total_unrealized_pl に total_pl の値を戻す
    op.execute(
        """
        UPDATE portfolio_history
        SET total_unrealized_pl = total_pl
    """
    )

    op.drop_column("portfolio_history", "total_pl")
    op.drop_column("holdings", "total_pl")
