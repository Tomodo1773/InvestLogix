from datetime import datetime
from typing import List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from .. import models, schemas


class PortfolioService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _calculate_portfolio_summary(self, user_id: int) -> dict:
        """ポートフォリオのサマリー情報を計算する内部メソッド"""
        holdings_query = select(models.Holding).where(models.Holding.user_id == user_id)
        holdings_result = await self.db.execute(holdings_query)
        holdings = holdings_result.scalars().all()

        holdings_by_market = {}
        holdings_by_currency = {}
        total_market_value = 0
        total_cost = 0
        total_realized_pl = 0

        for holding in holdings:
            stock_query = select(models.Stock).where(models.Stock.symbol == holding.symbol)
            stock_result = await self.db.execute(stock_query)
            stock = stock_result.scalar_one_or_none()

            market_value = holding.market_value or 0
            holdings_by_market[stock.market] = holdings_by_market.get(stock.market, 0) + market_value
            holdings_by_currency[stock.currency] = holdings_by_currency.get(stock.currency, 0) + market_value

            total_market_value += market_value
            total_cost += holding.total_cost
            total_realized_pl += holding.realized_pl or 0

        dividend_query = select(func.sum(models.Dividend.total_amount)).where(models.Dividend.user_id == user_id)
        dividend_result = await self.db.execute(dividend_query)
        total_dividend = dividend_result.scalar() or 0

        return {
            "total_cost": total_cost,
            "total_market_value": total_market_value,
            "total_unrealized_pl": total_market_value - total_cost,
            "total_unrealized_pl_percentage": (total_market_value - total_cost) / total_cost * 100 if total_cost > 0 else 0,
            "total_realized_pl": total_realized_pl,
            "total_dividend": total_dividend,
            "holdings_by_market": holdings_by_market,
            "holdings_by_currency": holdings_by_currency,
        }

    async def get_portfolio_summary(self, user_id: int) -> schemas.PortfolioSummary:
        """ポートフォリオのサマリー情報を取得"""
        summary = await self._calculate_portfolio_summary(user_id)
        return schemas.PortfolioSummary(**summary)

    async def get_portfolio_history(self, user_id: int) -> List[models.PortfolioHistory]:
        """ポートフォリオの履歴一覧を取得"""
        query = (
            select(models.PortfolioHistory)
            .where(models.PortfolioHistory.user_id == user_id)
            .order_by(models.PortfolioHistory.date.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def create_portfolio_history(self, user_id: int) -> models.PortfolioHistory:
        """現在のポートフォリオ状態を履歴として保存"""
        summary = await self._calculate_portfolio_summary(user_id)

        portfolio_history = models.PortfolioHistory(
            user_id=user_id,
            date=datetime.now(),
            **{k: v for k, v in summary.items() if k not in ["holdings_by_market", "holdings_by_currency"]},
        )

        self.db.add(portfolio_history)
        await self.db.commit()
        await self.db.refresh(portfolio_history)

        return portfolio_history

    async def get_latest_portfolio_history(self, user_id: int) -> models.PortfolioHistory:
        """最新のポートフォリオ履歴を取得"""
        query = (
            select(models.PortfolioHistory)
            .where(models.PortfolioHistory.user_id == user_id)
            .order_by(models.PortfolioHistory.date.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
