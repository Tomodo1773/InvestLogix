import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

import pandas as pd
import pandas_datareader.data as web
import pytz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .jquants_service import jquants_client
from ..models import Holding, Stock
from ..schemas import SecurityType
from ..services import alphavantage_service, investment_trust_service


async def get_japan_stock_price(symbol: str) -> Decimal:
    """
    日本株の株価を取得します。

    Args:
        symbol (str): 証券コード

    Returns:
        Decimal: 最新株価。取得できない場合は0
    """
    try:
        # 日本時間で1週間分のデータ期間を設定
        jst = pytz.timezone("Asia/Tokyo")
        now = datetime.now(jst)
        end_date = now.strftime("%Y-%m-%d")
        start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")

        # 非同期でJ-Quants APIを呼び出し
        prices = await jquants_client.get_prices(symbol=symbol, start_date=start_date, end_date=end_date)

        # 最新の株価を返す
        if prices and len(prices) > 0:
            return Decimal(str(prices[0].get("Close", "0")))
        return Decimal("0")

    except Exception as e:
        print(f"Error fetching Japan stock price for {symbol}: {str(e)}")
        return Decimal("0")


async def get_us_stock_price(symbol: str) -> Decimal:
    """
    米国株・ETFの株価を取得します。
    株価は円換算して返します。

    Args:
        symbol (str): ティッカーシンボル

    Returns:
        Decimal: 最新株価（円換算後）。取得できない場合は0
    """
    try:
        # まず為替レートを取得
        usdjpy_rate = await alphavantage_service.fetch_usdjpy_rate()
        if not usdjpy_rate:
            print(f"Failed to fetch USD/JPY rate for {symbol}")
            return Decimal("0")

        # 1週間前の日付を取得（日本時間）
        end = datetime.now(pytz.utc).astimezone(pytz.timezone("Asia/Tokyo"))
        start = end - timedelta(days=7)

        # stooqから株価データを取得（非同期処理のためにループで実行）
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, web.DataReader, symbol, "stooq", start, end)

        # 最新の終値を取得（データは新しい順）
        if not df.empty and "Close" in df.columns and len(df["Close"]) > 0:
            latest_close = df["Close"].iloc[0]
            if not pd.isna(latest_close):  # NaN値のチェック
                # 円換算して返す
                return Decimal(str(latest_close)) * Decimal(str(usdjpy_rate))

        return Decimal("0")

    except Exception as e:
        print(f"Error fetching US stock price for {symbol}: {str(e)}")
        return Decimal("0")


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
            # 日本株の場合
            return await get_japan_stock_price(stock.symbol)
        elif stock.currency == "USD":
            # 米国株の株価を取得
            return await get_us_stock_price(stock.symbol)
    elif stock.security_type == SecurityType.ETF and stock.currency == "USD":
        # 米国ETFの株価を取得（米国株と同じロジック）
        return await get_us_stock_price(stock.symbol)
    elif stock.security_type == SecurityType.FUND:
        # 投資信託の場合は投資信託ライブラリの基準価額を使用
        return await investment_trust_service.get_fund_price(stock.symbol)
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

    # 現在値情報を更新
    holding.current_price = current_price
    holding.market_value = current_price * holding.quantity
    holding.unrealized_pl = holding.market_value + holding.realized_pl + holding.total_dividend - holding.total_cost

    # パーセンテージ計算（データベースの制約に合わせて範囲を制限）
    if holding.total_cost != 0:
        pl_percentage = holding.unrealized_pl / holding.total_cost * 100
        # NUMERIC(5,2)の制約に合わせて、最大値を999.99に制限
        if pl_percentage > Decimal("999.99"):
            pl_percentage = Decimal("999.99")
        elif pl_percentage < Decimal("-999.99"):
            pl_percentage = Decimal("-999.99")
        holding.unrealized_pl_percentage = pl_percentage
    else:
        holding.unrealized_pl_percentage = Decimal("0")

    await db.commit()
    await db.refresh(holding)

    return holding


async def list_holdings(db: AsyncSession, user_id: int) -> List[Holding]:
    query = select(Holding, Stock.name).join(Stock, Holding.symbol == Stock.symbol).where(Holding.user_id == user_id)
    result = await db.execute(query)
    holdings = []
    for row in result:
        holding = row[0]
        holding.stock_name = row[1]
        holdings.append(holding)
    return holdings
