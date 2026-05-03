"""enable RLS on shared tables (warning suppression only)

Revision ID: b1c2d3e4f5a6
Revises: c1d2e3f4a5b6
Create Date: 2026-05-03 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Supabaseの「RLS未有効」警告を抑止するためにENABLEだけ行う共有/メタテーブル。
# ポリシーは設定しないため、テーブルオーナー(postgres)からは通常通りアクセス可能。
SHARED_TABLES = [
    "stocks",
    "stock_jpx_details",
    "stock_us_details",
    "users",
    "alembic_version",
]


def upgrade() -> None:
    for table in SHARED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    for table in reversed(SHARED_TABLES):
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
