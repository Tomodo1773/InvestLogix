import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

import pandas as pd
import pandas_datareader.data as web
import pytz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Holding, Stock
from ..schemas import SecurityType
from ..services import alphavantage_service, investment_trust_service
from .jquants_service import jquants_client


async def get_japan_stock_price(symbol: str) -> Decimal:
    """
    日本株の最新株価を取得します。

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
    米国株・ETFの最新株価を円換算して取得します。

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
    日本株、米国株、米国ETF、投資信託に対応します。

    Args:
        stock (Stock): 銘柄情報

    Returns:
        Decimal: 最新株価
    """
    if stock.security_type == SecurityType.STOCK:
        if stock.currency == "JPY":
            return await get_japan_stock_price(stock.symbol)
        elif stock.currency == "USD":
            return await get_us_stock_price(stock.symbol)
    elif stock.security_type == SecurityType.ETF and stock.currency == "USD":
        return await get_us_stock_price(stock.symbol)
    elif stock.security_type == SecurityType.FUND:
        return await investment_trust_service.get_fund_price(stock.symbol)
    return Decimal("0")


async def calculate_holding_pl(db: AsyncSession, user_id: int, symbol: str, stock: Stock) -> Holding:
    """
    指定された銘柄の保有損益を計算します。
    データベースへの保存は行いません。

    Args:
        db (AsyncSession): 非同期データベースセッション
        user_id (int): ユーザーID
        symbol (str): 銘柄コード
        stock (Stock): 銘柄情報

    Returns:
        Holding: 損益計算後の保有情報
    """
    # 保有情報を取得
    stmt = select(Holding).filter(Holding.user_id == user_id, Holding.symbol == symbol)
    result = await db.execute(stmt)
    holding = result.scalar_one_or_none()

    if not holding:
        return None

    # 最新株価を取得
    current_price = await get_current_price(stock)

    # 現在値情報を更新
    holding.current_price = current_price
    holding.market_value = current_price * holding.quantity
    holding.unrealized_pl = holding.market_value + holding.realized_pl + holding.total_dividend - holding.total_cost

    # パーセンテージ計算（データベースの制約に合わせて範囲を制限）
    if holding.total_cost != 0:
        pl_percentage = holding.unrealized_pl / holding.total_cost * 100
        if pl_percentage > Decimal("999.99"):
            pl_percentage = Decimal("999.99")
        elif pl_percentage < Decimal("-999.99"):
            pl_percentage = Decimal("-999.99")
        holding.unrealized_pl_percentage = pl_percentage
    else:
        holding.unrealized_pl_percentage = Decimal("0")

    return holding


async def update_single_holding_pl(db: AsyncSession, user_id: int, symbol: str) -> Holding:
    """
    指定された単一銘柄の保有損益を再計算し、データベースを更新します。

    Args:
        db (AsyncSession): 非同期データベースセッション
        user_id (int): ユーザーID
        symbol (str): 銘柄コード

    Returns:
        Holding: 更新された保有情報
    """
    # 銘柄情報を取得
    stmt = select(Stock).filter(Stock.symbol == symbol)
    result = await db.execute(stmt)
    stock = result.scalar_one_or_none()

    if not stock:
        return None

    holding = await calculate_holding_pl(db, user_id, symbol, stock)
    if holding:
        await db.commit()
        await db.refresh(holding)

    return holding


async def update_all_holdings_pl(db: AsyncSession, user_id: int) -> List[Holding]:
    """
    ユーザーの保有する全銘柄の損益を一括更新します。

    Args:
        db (AsyncSession): 非同期データベースセッション
        user_id (int): ユーザーID

    Returns:
        List[Holding]: 更新された保有情報のリスト
    """
    # 保有銘柄一覧を取得
    holdings = await list_holdings(db, user_id)
    updated_holdings = []

    # 銘柄情報を事前に取得
    symbols = [h.symbol for h in holdings]
    stmt = select(Stock).filter(Stock.symbol.in_(symbols))
    result = await db.execute(stmt)
    stocks = {stock.symbol: stock for stock in result.scalars()}

    # 各銘柄を更新
    for holding in holdings:
        stock = stocks.get(holding.symbol)
        if stock:
            updated = await calculate_holding_pl(db, user_id, holding.symbol, stock)
            if updated:
                updated_holdings.append(updated)

    # 一括でコミット
    await db.commit()

    # 更新後のデータをリフレッシュ
    for holding in updated_holdings:
        await db.refresh(holding)

    return updated_holdings


async def list_holdings(db: AsyncSession, user_id: int) -> List[Holding]:
    """
    ユーザーの保有銘柄一覧を銘柄名と共に取得します。

    Args:
        db (AsyncSession): 非同期データベースセッション
        user_id (int): ユーザーID

    Returns:
        List[Holding]: 銘柄名を含む保有銘柄情報のリスト
    """
    query = select(Holding, Stock.name).join(Stock, Holding.symbol == Stock.symbol).where(Holding.user_id == user_id)
    result = await db.execute(query)
    holdings = []
    for row in result:
        holding = row[0]
        holding.stock_name = row[1]
        holdings.append(holding)
    return holdings
