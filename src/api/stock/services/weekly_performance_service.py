"""
週間パフォーマンス計算サービス
保有銘柄の週間騰落率を計算し、上位・下位5位を抽出する
"""

from typing import List, Optional, Tuple

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from ..schemas import SecurityType, StockWeeklyPerformance
from .stock_price_fetcher import fetch_japan_stock_prices, fetch_us_stock_prices


async def get_japan_stock_weekly_prices(symbol: str) -> Optional[Tuple[float, float]]:
    """
    日本株の最新株価と5営業日前の株価を取得します。

    Args:
        symbol (str): 証券コード

    Returns:
        Optional[Tuple[float, float]]: (最新株価, 5営業日前株価)。取得できない場合はNone
    """
    # 2週間分のデータを取得（営業日を確実に取得するため余裕を持つ）
    prices = await fetch_japan_stock_prices(symbol, days_back=14)

    # 6件以上のデータが必要（最新と5営業日前）
    if prices and len(prices) >= 6:
        latest_price = float(prices[-1].get("AdjC", "0"))
        old_price = float(prices[-6].get("AdjC", "0"))
        return (latest_price, old_price)
    return None


async def get_us_stock_weekly_prices(symbol: str) -> Optional[Tuple[float, float]]:
    """
    米国株の最新株価と5営業日前の株価を取得します。
    ※ 騰落率計算のため、円換算は行わず米ドル建てで返します。

    Args:
        symbol (str): ティッカーシンボル

    Returns:
        Optional[Tuple[float, float]]: (最新株価, 5営業日前株価)。取得できない場合はNone
    """
    # 2週間分のデータを取得（営業日を確実に取得するため余裕を持つ）
    prices = await fetch_us_stock_prices(symbol, days_back=14)

    # 返却は古い順なので末尾が最新、6件目後ろが5営業日前
    if len(prices) >= 6:
        latest_price = float(prices[-1]["close"])
        old_price = float(prices[-6]["close"])
        return (latest_price, old_price)

    return None


async def calculate_weekly_performance(db: AsyncSession, user_id: int) -> List[StockWeeklyPerformance]:
    """
    保有銘柄の週間騰落率を計算します。
    保有数量が0の銘柄と投資信託（FUND）は除外します。

    Args:
        db (AsyncSession): データベースセッション
        user_id (int): ユーザーID

    Returns:
        List[StockWeeklyPerformance]: 騰落率情報のリスト
    """
    # 保有銘柄を取得（保有数量 > 0の銘柄のみ）
    query = (
        select(models.Holding, models.Stock)
        .join(models.Stock, models.Holding.symbol == models.Stock.symbol)
        .where(
            models.Holding.user_id == user_id,
            models.Holding.quantity > 0,
        )
    )
    result = await db.execute(query)
    holdings_with_stocks = result.all()

    performances = []

    for holding, stock in holdings_with_stocks:
        # 投資信託は除外
        if stock.security_type == SecurityType.FUND.value:
            continue

        prices = None

        # 日本株の場合
        if stock.currency == "JPY" and stock.security_type in [
            SecurityType.STOCK.value,
            SecurityType.ETF.value,
            SecurityType.REIT.value,
        ]:
            prices = await get_japan_stock_weekly_prices(stock.symbol)

        # 米国株・ETFの場合
        elif stock.currency == "USD" and stock.security_type in [
            SecurityType.STOCK.value,
            SecurityType.ETF.value,
        ]:
            prices = await get_us_stock_weekly_prices(stock.symbol)

        if prices and prices[0] > 0 and prices[1] > 0:
            latest_price, old_price = prices
            # 騰落率を計算: (最新 - 5営業日前) / 5営業日前 * 100
            change_rate = (latest_price - old_price) / old_price * 100

            performances.append(
                StockWeeklyPerformance(
                    symbol=stock.symbol,
                    name=stock.name,
                    latest_price=latest_price,
                    old_price=old_price,
                    change_rate=round(change_rate, 2),
                )
            )

    logger.info(
        "週間騰落率を取得しました action=aggregate user_id={} count={}",
        user_id,
        len(performances),
    )
    return performances


def get_top_bottom_performers(
    performances: List[StockWeeklyPerformance], n: int = 5
) -> Tuple[List[StockWeeklyPerformance], List[StockWeeklyPerformance]]:
    """
    騰落率の上位・下位n位を抽出します。

    Args:
        performances (List[StockWeeklyPerformance]): パフォーマンス情報のリスト
        n (int): 抽出する件数（デフォルト5）

    Returns:
        Tuple[List[StockWeeklyPerformance], List[StockWeeklyPerformance]]:
            (上位n位, 下位n位)
    """
    # 騰落率でソート
    sorted_performances = sorted(performances, key=lambda x: x.change_rate, reverse=True)

    # 上位n位と下位n位を抽出
    top_performers = sorted_performances[:n]
    if len(sorted_performances) >= n:
        bottom_performers = sorted_performances[-n:][::-1]
    else:
        bottom_performers = sorted_performances[::-1]

    return top_performers, bottom_performers
