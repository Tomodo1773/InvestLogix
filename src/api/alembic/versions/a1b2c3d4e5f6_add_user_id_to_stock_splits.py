"""stock_splitsテーブルにuser_idカラムを追加

Revision ID: a1b2c3d4e5f6
Revises: 0b8f7bee9310
Create Date: 2026-01-09 23:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "0b8f7bee9310"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. user_idカラムを追加（一時的にnullable=True）
    op.add_column("stock_splits", sa.Column("user_id", sa.Integer(), nullable=True))

    # 2. 外部キー制約を追加
    op.create_foreign_key(
        "fk_stock_splits_user_id",
        "stock_splits",
        "users",
        ["user_id"],
        ["user_id"],
    )

    # 3. 古いユニーク制約を削除
    op.drop_constraint("uq_symbol_split_date", "stock_splits", type_="unique")

    # 4. 新しいユニーク制約を追加（user_id, symbol, split_date）
    op.create_unique_constraint(
        "uq_user_symbol_split_date",
        "stock_splits",
        ["user_id", "symbol", "split_date"],
    )


def downgrade() -> None:
    # 1. 新しいユニーク制約を削除
    op.drop_constraint("uq_user_symbol_split_date", "stock_splits", type_="unique")

    # 2. 古いユニーク制約を復元
    op.create_unique_constraint("uq_symbol_split_date", "stock_splits", ["symbol", "split_date"])

    # 3. 外部キー制約を削除
    op.drop_constraint("fk_stock_splits_user_id", "stock_splits", type_="foreignkey")

    # 4. user_idカラムを削除
    op.drop_column("stock_splits", "user_id")
