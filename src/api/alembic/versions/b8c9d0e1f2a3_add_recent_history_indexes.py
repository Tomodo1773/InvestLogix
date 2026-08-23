"""add recent history indexes

Revision ID: b8c9d0e1f2a3
Revises: a7c8d9e0f1b2
Create Date: 2026-08-23 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7c8d9e0f1b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_transactions_user_id_transaction_date_transaction_id",
        "transactions",
        ["user_id", "transaction_date", "transaction_id"],
        unique=False,
    )
    op.create_index(
        "ix_dividend_user_id_payment_date_dividend_id",
        "dividend",
        ["user_id", "payment_date", "dividend_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_dividend_user_id_payment_date_dividend_id", table_name="dividend")
    op.drop_index("ix_transactions_user_id_transaction_date_transaction_id", table_name="transactions")
