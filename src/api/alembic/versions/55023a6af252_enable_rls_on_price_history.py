"""enable RLS on price_history

Revision ID: 55023a6af252
Revises: 6ce2935178c1
Create Date: 2026-05-12 15:46:17.634532

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "55023a6af252"
down_revision: Union[str, None] = "6ce2935178c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# price_history はユーザーに紐付かない共有データ。
# Supabaseの「RLS未有効」警告を抑止するためにENABLEだけ行う。
# ポリシーは設定しないため、テーブルオーナー(postgres)からは通常通りアクセス可能。


def upgrade() -> None:
    op.execute("ALTER TABLE price_history ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("ALTER TABLE price_history DISABLE ROW LEVEL SECURITY")
