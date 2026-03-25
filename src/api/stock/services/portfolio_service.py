from datetime import timedelta
from typing import Dict, List

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas
from ..services.holding_service import update_all_holdings_pl
from ..services.notification_service import NotificationService
from ..utils.datetime import now_jst


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

        # 配当の集計（税引後金額を計算）
        dividend_query = select(
            func.sum(models.Dividend.total_amount - func.coalesce(models.Dividend.tax, 0))
        ).where(models.Dividend.user_id == user_id)
        dividend_result = await self.db.execute(dividend_query)
        total_dividend = float(dividend_result.scalar() or 0)

        # 全体損益の計算
        total_unrealized_pl = total_market_value - total_cost
        total_pl = total_unrealized_pl + total_realized_pl + total_dividend
        total_pl_percentage = (total_pl / total_cost * 100) if total_cost > 0 else 0

        logger.info(
            "PortfolioSummaryを集計しました action=aggregate user_id={} holdings_count={}",
            user_id,
            len(holdings),
        )
        return {
            "total_cost": total_cost,
            "total_market_value": total_market_value,
            "total_unrealized_pl": total_unrealized_pl,
            "total_unrealized_pl_percentage": (total_market_value - total_cost) / total_cost * 100
            if total_cost > 0
            else 0,
            "total_realized_pl": total_realized_pl,
            "total_dividend": total_dividend,
            "total_pl": total_pl,
            "total_pl_percentage": total_pl_percentage,
            "holdings_by_market": holdings_by_market,
            "holdings_by_currency": holdings_by_currency,
        }

    async def get_portfolio_summary(self, user_id: int) -> schemas.PortfolioSummary:
        """ポートフォリオのサマリー情報を計算して取得"""
        summary = await self._calculate_portfolio_summary(user_id)
        return schemas.PortfolioSummary(**summary)

    async def get_portfolio_history(self, user_id: int) -> List[models.PortfolioHistory]:
        """ポートフォリオの履歴一覧を取得

        日付の昇順（古い順）でポートフォリオの履歴を返します。
        """
        query = (
            select(models.PortfolioHistory)
            .where(models.PortfolioHistory.user_id == user_id)
            .order_by(models.PortfolioHistory.date.asc())  # 降順(desc)から昇順(asc)に変更
        )
        result = await self.db.execute(query)
        histories = result.scalars().all()
        logger.info(
            "PortfolioHistoryを取得しました action=select user_id={} count={}",
            user_id,
            len(histories),
        )
        return histories

    async def create_portfolio_history(self, user_id: int) -> models.PortfolioHistory:
        """現在のポートフォリオ状態を計算して履歴として保存"""
        summary = await self._calculate_portfolio_summary(user_id)

        portfolio_history = models.PortfolioHistory(
            user_id=user_id,
            date=now_jst(),
            **{k: v for k, v in summary.items() if k not in ["holdings_by_market", "holdings_by_currency"]},
        )

        self.db.add(portfolio_history)
        await self.db.flush()
        await self.db.refresh(portfolio_history)

        logger.info(
            "PortfolioHistoryを登録しました action=create user_id={} history_id={}",
            user_id,
            portfolio_history.history_id,
        )
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
        history = result.scalar_one_or_none()
        if not history:
            logger.info(
                "PortfolioHistoryが見つかりませんでした action=select user_id={} found=false",
                user_id,
            )
            return None
        logger.info(
            "PortfolioHistoryを取得しました action=select user_id={} history_id={} found=true",
            user_id,
            history.history_id,
        )
        return history

    async def update_and_notify(self, user_id: int) -> Dict:
        """
        ポートフォリオの全銘柄を更新し、履歴を保存し、LINEに通知する

        Args:
            user_id (int): ユーザーID

        Returns:
            Dict: 処理結果とポートフォリオサマリー
        """
        # 全銘柄の最新株価を取得して更新
        await update_all_holdings_pl(self.db, user_id)

        # ポートフォリオの状態を履歴に保存
        portfolio_history = await self.create_portfolio_history(user_id)

        # 前週のデータを取得して差額を計算
        week_ago = now_jst() - timedelta(days=6)
        prev_query = (
            select(models.PortfolioHistory)
            .where(
                models.PortfolioHistory.user_id == user_id,
                models.PortfolioHistory.date <= week_ago,
            )
            .order_by(models.PortfolioHistory.date.desc())
            .limit(1)
        )
        prev_result = await self.db.execute(prev_query)
        prev_history = prev_result.scalar_one_or_none()
        weekly_change = portfolio_history.total_pl - prev_history.total_pl if prev_history else None

        # SQLAlchemy modelをPythonの辞書に変換
        portfolio_data = {
            "total_cost": portfolio_history.total_cost,
            "total_market_value": portfolio_history.total_market_value,
            "total_pl": portfolio_history.total_pl,
            "total_pl_percentage": portfolio_history.total_pl_percentage,
            "total_realized_pl": portfolio_history.total_realized_pl,
            "total_dividend": portfolio_history.total_dividend,
            "weekly_change": weekly_change,
        }

        # LINE通知を送信（DBセッションも渡す）
        notification_sent = await NotificationService.send_line_notification(user_id, portfolio_data, self.db)

        # ポートフォリオサマリーを取得
        summary = await self.get_portfolio_summary(user_id)

        logger.info(
            "Portfolioを更新しました action=bulk_update user_id={} notification_sent={}",
            user_id,
            notification_sent,
        )
        return {
            "summary": summary,
            "notification_sent": notification_sent,
            "timestamp": now_jst().isoformat(),
        }
