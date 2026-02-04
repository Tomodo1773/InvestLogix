"""Change numeric columns to float

Revision ID: f8e7d6c5b4a3
Revises: e9bc1da32174
Create Date: 2026-02-03 06:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f8e7d6c5b4a3"
down_revision: Union[str, None] = "e9bc1da32174"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # StockSplit table
    op.alter_column("stock_splits", "split_ratio", type_=sa.Float(), existing_nullable=False)

    # Holding table
    op.alter_column("holdings", "quantity", type_=sa.Float(), existing_nullable=False)
    op.alter_column("holdings", "average_cost", type_=sa.Float(), existing_nullable=False)
    op.alter_column("holdings", "total_cost", type_=sa.Float(), existing_nullable=False)
    op.alter_column("holdings", "current_price", type_=sa.Float(), existing_nullable=True)
    op.alter_column("holdings", "market_value", type_=sa.Float(), existing_nullable=True)
    op.alter_column("holdings", "realized_pl", type_=sa.Float(), existing_nullable=True)
    op.alter_column("holdings", "total_dividend", type_=sa.Float(), existing_nullable=True)
    op.alter_column("holdings", "unrealized_pl", type_=sa.Float(), existing_nullable=True)
    op.alter_column("holdings", "unrealized_pl_percentage", type_=sa.Float(), existing_nullable=True)
    op.alter_column("holdings", "total_pl", type_=sa.Float(), existing_nullable=True)
    op.alter_column("holdings", "total_pl_percentage", type_=sa.Float(), existing_nullable=True)

    # Transaction table
    op.alter_column("transactions", "quantity", type_=sa.Float(), existing_nullable=False)
    op.alter_column("transactions", "price", type_=sa.Float(), existing_nullable=False)
    op.alter_column("transactions", "usd_price", type_=sa.Float(), existing_nullable=True)
    op.alter_column("transactions", "adjusted_price", type_=sa.Float(), existing_nullable=True)
    op.alter_column("transactions", "adjusted_quantity", type_=sa.Float(), existing_nullable=True)
    op.alter_column("transactions", "fee", type_=sa.Float(), existing_nullable=False)
    op.alter_column("transactions", "tax", type_=sa.Float(), existing_nullable=False)
    op.alter_column("transactions", "realized_pl", type_=sa.Float(), existing_nullable=False)

    # PortfolioHistory table
    op.alter_column("portfolio_history", "total_cost", type_=sa.Float(), existing_nullable=False)
    op.alter_column("portfolio_history", "total_market_value", type_=sa.Float(), existing_nullable=False)
    op.alter_column("portfolio_history", "total_unrealized_pl", type_=sa.Float(), existing_nullable=False)
    op.alter_column(
        "portfolio_history", "total_unrealized_pl_percentage", type_=sa.Float(), existing_nullable=False
    )
    op.alter_column("portfolio_history", "total_realized_pl", type_=sa.Float(), existing_nullable=False)
    op.alter_column("portfolio_history", "total_dividend", type_=sa.Float(), existing_nullable=False)
    op.alter_column("portfolio_history", "total_pl", type_=sa.Float(), existing_nullable=False)
    op.alter_column("portfolio_history", "total_pl_percentage", type_=sa.Float(), existing_nullable=False)

    # Dividend table
    op.alter_column("dividend", "shares_owned", type_=sa.Float(), existing_nullable=False)
    op.alter_column("dividend", "total_amount", type_=sa.Float(), existing_nullable=False)
    op.alter_column("dividend", "tax", type_=sa.Float(), existing_nullable=True)
    op.alter_column("dividend", "fee", type_=sa.Float(), existing_nullable=True)


def downgrade() -> None:
    # StockSplit table
    op.alter_column("stock_splits", "split_ratio", type_=sa.Numeric(10, 4), existing_nullable=False)

    # Holding table
    op.alter_column("holdings", "quantity", type_=sa.Numeric(10, 4), existing_nullable=False)
    op.alter_column("holdings", "average_cost", type_=sa.Numeric(10, 2), existing_nullable=False)
    op.alter_column("holdings", "total_cost", type_=sa.Numeric(10, 2), existing_nullable=False)
    op.alter_column("holdings", "current_price", type_=sa.Numeric(10, 2), existing_nullable=True)
    op.alter_column("holdings", "market_value", type_=sa.Numeric(10, 2), existing_nullable=True)
    op.alter_column("holdings", "realized_pl", type_=sa.Numeric(10, 2), existing_nullable=True)
    op.alter_column("holdings", "total_dividend", type_=sa.Numeric(10, 2), existing_nullable=True)
    op.alter_column("holdings", "unrealized_pl", type_=sa.Numeric(10, 2), existing_nullable=True)
    op.alter_column("holdings", "unrealized_pl_percentage", type_=sa.Numeric(5, 2), existing_nullable=True)
    op.alter_column("holdings", "total_pl", type_=sa.Numeric(10, 2), existing_nullable=True)
    op.alter_column("holdings", "total_pl_percentage", type_=sa.Numeric(5, 2), existing_nullable=True)

    # Transaction table
    op.alter_column("transactions", "quantity", type_=sa.Numeric(10, 4), existing_nullable=False)
    op.alter_column("transactions", "price", type_=sa.Numeric(10, 2), existing_nullable=False)
    op.alter_column("transactions", "usd_price", type_=sa.Numeric(10, 2), existing_nullable=True)
    op.alter_column("transactions", "adjusted_price", type_=sa.Numeric(10, 2), existing_nullable=True)
    op.alter_column("transactions", "adjusted_quantity", type_=sa.Numeric(10, 4), existing_nullable=True)
    op.alter_column("transactions", "fee", type_=sa.Numeric(10, 2), existing_nullable=False)
    op.alter_column("transactions", "tax", type_=sa.Numeric(10, 2), existing_nullable=False)
    op.alter_column("transactions", "realized_pl", type_=sa.Numeric(10, 2), existing_nullable=False)

    # PortfolioHistory table
    op.alter_column("portfolio_history", "total_cost", type_=sa.Numeric(10, 2), existing_nullable=False)
    op.alter_column(
        "portfolio_history", "total_market_value", type_=sa.Numeric(10, 2), existing_nullable=False
    )
    op.alter_column(
        "portfolio_history", "total_unrealized_pl", type_=sa.Numeric(10, 2), existing_nullable=False
    )
    op.alter_column(
        "portfolio_history",
        "total_unrealized_pl_percentage",
        type_=sa.Numeric(5, 2),
        existing_nullable=False,
    )
    op.alter_column(
        "portfolio_history", "total_realized_pl", type_=sa.Numeric(10, 2), existing_nullable=False
    )
    op.alter_column("portfolio_history", "total_dividend", type_=sa.Numeric(10, 2), existing_nullable=False)
    op.alter_column("portfolio_history", "total_pl", type_=sa.Numeric(10, 2), existing_nullable=False)
    op.alter_column(
        "portfolio_history", "total_pl_percentage", type_=sa.Numeric(5, 2), existing_nullable=False
    )

    # Dividend table
    op.alter_column("dividend", "shares_owned", type_=sa.Numeric(10, 4), existing_nullable=False)
    op.alter_column("dividend", "total_amount", type_=sa.Numeric(10, 2), existing_nullable=False)
    op.alter_column("dividend", "tax", type_=sa.Numeric(10, 2), existing_nullable=True)
    op.alter_column("dividend", "fee", type_=sa.Numeric(10, 2), existing_nullable=True)
