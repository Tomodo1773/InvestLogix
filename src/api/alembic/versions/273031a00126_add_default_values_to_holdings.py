"""add default values to holdings

Revision ID: 273031a00126
Revises: e69f37e6ae41
Create Date: 2024-03-17 17:30:00.000000

"""

from decimal import Decimal
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "273031a00126"
down_revision: Union[str, None] = "e69f37e6ae41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 既存のNULLデータを0に更新
    op.execute(
        """
        UPDATE holdings 
        SET realized_pl = '0' 
        WHERE realized_pl IS NULL
        """
    )
    op.execute(
        """
        UPDATE holdings 
        SET total_dividend = '0' 
        WHERE total_dividend IS NULL
        """
    )

    # デフォルト値の設定
    with op.batch_alter_table("holdings") as batch_op:
        batch_op.alter_column(
            "realized_pl", existing_type=sa.Numeric(10, 2), server_default=sa.text("'0'"), existing_nullable=True
        )
        batch_op.alter_column(
            "total_dividend", existing_type=sa.Numeric(10, 2), server_default=sa.text("'0'"), existing_nullable=True
        )


def downgrade() -> None:
    # デフォルト値の削除
    with op.batch_alter_table("holdings") as batch_op:
        batch_op.alter_column("realized_pl", existing_type=sa.Numeric(10, 2), server_default=None, existing_nullable=True)
        batch_op.alter_column("total_dividend", existing_type=sa.Numeric(10, 2), server_default=None, existing_nullable=True)
