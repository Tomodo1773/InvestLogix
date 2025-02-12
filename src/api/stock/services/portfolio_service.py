from typing import List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas


class PortfolioService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_portfolio_summary(self, user_id: int) -> schemas.PortfolioSummary:
        holdings_query = select(models.Holding).where(models.Holding.user_id == user_id)
        holdings_result = await self.db.execute(holdings_query)
        holdings = holdings_result.scalars().all()

        holdings_by_market = {}
        holdings_by_currency = {}
        total_market_value = 0
        total_cost = 0

        for holding in holdings:
            stock_query = select(models.Stock).where(models.Stock.symbol == holding.symbol)
            stock_result = await self.db.execute(stock_query)
            stock = stock_result.scalar_one_or_none()

            market_value = holding.market_value or 0
            holdings_by_market[stock.market] = holdings_by_market.get(stock.market, 0) + market_value
            holdings_by_currency[stock.currency] = holdings_by_currency.get(stock.currency, 0) + market_value

            total_market_value += market_value
            total_cost += holding.total_cost

        dividend_query = select(func.sum(models.Dividend.total_amount)).where(models.Dividend.user_id == user_id)
        dividend_result = await self.db.execute(dividend_query)
        total_dividend = dividend_result.scalar() or 0

        return schemas.PortfolioSummary(
            total_cost=total_cost,
            total_market_value=total_market_value,
            total_unrealized_pl=total_market_value - total_cost,
            total_unrealized_pl_percentage=(total_market_value - total_cost) / total_cost * 100 if total_cost > 0 else 0,
            total_realized_pl=0,  # TODO: 実現損益の計算を実装
            total_dividend=total_dividend,
            cash_balance=0,  # TODO: 現金残高の計算を実装
            holdings_by_market=holdings_by_market,
            holdings_by_currency=holdings_by_currency,
        )

    async def list_holdings(self, user_id: int) -> List[models.Holding]:
        query = select(models.Holding).where(models.Holding.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalars().all()
