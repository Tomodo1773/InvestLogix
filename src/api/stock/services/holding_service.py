import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

import pytz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..jquants import jquants_client
from ..models import Holding, Stock
from ..schemas import SecurityType


async def get_current_price(stock: Stock) -> Decimal:
    """
    証券種別と通貨に基づいて最新株価を取得します。
    日本株、米国株、米国ETF、投資信託の4つの主要な証券タイプに対応します。

    Args:
        stock (Stock): 銘柄情報

    Returns:
        Decimal: 最新株価
    """
    if stock.security_type == SecurityType.STOCK:
        if stock.currency == "JPY":
            # 日本株の場合はJ-Quants APIを使用
            jst = pytz.timezone("Asia/Tokyo")
            now = datetime.now(jst)
            end_date = now.strftime("%Y-%m-%d")
            start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")

            # 非同期でJ-Quants APIを呼び出し
            prices = await jquants_client.get_prices(symbol=stock.symbol, start_date=start_date, end_date=end_date)

            # 最新の株価を返す
            if prices and len(prices) > 0:
                return Decimal(str(prices[0].get("Close", "0")))
            return Decimal("0")
        elif stock.currency == "USD":
            # TODO: 米国株の株価取得ロジックを実装
            return Decimal("0")
    elif stock.security_type == SecurityType.ETF and stock.currency == "USD":
        # TODO: 米国ETFの価格取得ロジックを実装
        return Decimal("0")
    elif stock.security_type == SecurityType.FUND:
        # TODO: 投資信託の基準価額取得ロジックを実装
        return Decimal("0")
    else:
        return Decimal("0")


async def update_holding_pl(db: AsyncSession, user_id: int, symbol: str) -> Holding:
    """
    指定された銘柄の保有損益を再計算します。

    Args:
        db (AsyncSession): 非同期データベースセッション
        user_id (int): ユーザーID
        symbol (str): 銘柄コード

    Returns:
        Holding: 更新された保有情報
    """
    # 保有情報を取得
    stmt = select(Holding).filter(Holding.user_id == user_id, Holding.symbol == symbol)
    result = await db.execute(stmt)
    holding = result.scalar_one_or_none()

    if not holding:
        return None

    # 銘柄情報を取得
    stmt = select(Stock).filter(Stock.symbol == symbol)
    result = await db.execute(stmt)
    stock = result.scalar_one_or_none()

    # 最新株価を取得
    current_price = await get_current_price(stock)

    # 時価評価額を計算
    market_value = current_price * holding.quantity

    # 評価損益を計算
    unrealized_pl = market_value + holding.realized_pl + holding.total_dividend - holding.total_cost

    # 評価損益率を計算
    unrealized_pl_percentage = (unrealized_pl / holding.total_cost * 100) if holding.total_cost != 0 else Decimal("0")

    # 保有情報を更新
    holding.current_price = current_price
    holding.market_value = market_value
    holding.unrealized_pl = unrealized_pl
    holding.unrealized_pl_percentage = unrealized_pl_percentage

    await db.commit()
    await db.refresh(holding)

    return holding
