"""add transactions account holdings index

Revision ID: 1f2e3d4c5b6a
Revises: 7b1c2d3e4f5a
Create Date: 2026-07-10 11:10:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1f2e3d4c5b6a"
down_revision: str | None = "7b1c2d3e4f5a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_transactions_user_symbol_account_type",
        "transactions",
        ["user_id", "symbol", "account_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_user_symbol_account_type", table_name="transactions")
