"""remove cash_balance

Revision ID: 0d718c7298ee
Revises: 8eb30d065c88
Create Date: 2025-02-18 21:42:55.345189

"""

from decimal import Decimal
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0d718c7298ee"
down_revision: Union[str, None] = "8eb30d065c88"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLiteではカラムを直接削除できないため、テーブルを再作成する
    # 1. 現在のテーブルの構造を取得（cash_balanceを除く）
    columns = [
        sa.Column("history_id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("total_cost", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_market_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_unrealized_pl", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_unrealized_pl_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("total_realized_pl", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_dividend", sa.Numeric(10, 2), nullable=False),
    ]

    # 2. 一時テーブルを作成
    op.create_table(
        "portfolio_history_new",
        *columns,
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
        ),
        sa.UniqueConstraint("user_id", "date", name="uq_user_date_portfolio"),
    )

    # 3. データを移行
    op.execute("""
        INSERT INTO portfolio_history_new 
        SELECT history_id, user_id, date, total_cost, total_market_value, 
               total_unrealized_pl, total_unrealized_pl_percentage, 
               total_realized_pl, total_dividend
        FROM portfolio_history
    """)

    # 4. 古いテーブルを削除
    op.drop_table("portfolio_history")

    # 5. 新しいテーブルの名前を変更
    op.rename_table("portfolio_history_new", "portfolio_history")

    # holdingsテーブルのカラムにDEFAULT値を設定
    with op.batch_alter_table("holdings") as batch_op:
        batch_op.alter_column(
            "realized_pl", existing_type=sa.Numeric(10, 2), server_default=sa.text("0"), existing_nullable=True
        )
        batch_op.alter_column(
            "total_dividend", existing_type=sa.Numeric(10, 2), server_default=sa.text("0"), existing_nullable=True
        )


def downgrade() -> None:
    # holdingsテーブルのDEFAULT値を削除
    with op.batch_alter_table("holdings") as batch_op:
        batch_op.alter_column("realized_pl", existing_type=sa.Numeric(10, 2), server_default=None, existing_nullable=True)
        batch_op.alter_column("total_dividend", existing_type=sa.Numeric(10, 2), server_default=None, existing_nullable=True)

    # cash_balanceカラムを追加するために一時テーブルを作成
    columns = [
        sa.Column("history_id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("total_cost", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_market_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_unrealized_pl", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_unrealized_pl_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("total_realized_pl", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_dividend", sa.Numeric(10, 2), nullable=False),
        sa.Column("cash_balance", sa.Numeric(10, 2), nullable=True),
    ]

    op.create_table(
        "portfolio_history_new",
        *columns,
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
        ),
        sa.UniqueConstraint("user_id", "date", name="uq_user_date_portfolio"),
    )

    # データを移行（cash_balanceはNULLとして）
    op.execute("""
        INSERT INTO portfolio_history_new 
        SELECT history_id, user_id, date, total_cost, total_market_value, 
               total_unrealized_pl, total_unrealized_pl_percentage, 
               total_realized_pl, total_dividend, NULL
        FROM portfolio_history
    """)

    # 古いテーブルを削除
    op.drop_table("portfolio_history")

    # 新しいテーブルの名前を変更
    op.rename_table("portfolio_history_new", "portfolio_history")
