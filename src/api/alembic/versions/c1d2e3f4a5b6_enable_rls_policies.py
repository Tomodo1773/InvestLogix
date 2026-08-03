"""enable RLS policies for user data tables

Revision ID: c1d2e3f4a5b6
Revises: f8e7d6c5b4a3
Create Date: 2026-02-17 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "f8e7d6c5b4a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# RLSポリシーを適用するテーブルと対応するuser_idカラム
RLS_TABLES = [
    "holdings",
    "transactions",
    "dividend",
    "portfolio_history",
    "stock_splits",
]


def upgrade() -> None:
    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_user_isolation ON {table}
                USING (user_id = current_setting('app.current_user_id', true)::int)
            """
        )


def downgrade() -> None:
    for table in reversed(RLS_TABLES):
        op.execute(f"DROP POLICY IF EXISTS {table}_user_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
