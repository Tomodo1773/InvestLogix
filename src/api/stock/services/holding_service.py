import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

import pandas as pd
import pandas_datareader.data as web
import pytz
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
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
            return Decimal(str(prices[-1].get("Close", "0")))
        return Decimal("0")

    except Exception:
        logger.error(f"日本株株価取得エラー symbol={symbol}", exc_info=True)
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
            logger.warning(f"為替レート取得失敗 symbol={symbol}")
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

    except Exception:
        logger.error(f"米国株株価取得エラー symbol={symbol}", exc_info=True)
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
    logger.info(
        f"株価取得開始 symbol={stock.symbol}, security_type={stock.security_type}, currency={stock.currency}"
    )
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


async def calculate_holding_from_transactions(db: AsyncSession, user_id: int, symbol: str):
    """
    トランザクション履歴から保有数量と取得価格を計算する
    株式分割がある場合は調整済み値を使用する

    Args:
        db (AsyncSession): データベースセッション
        user_id (int): ユーザーID
        symbol (str): 銘柄コード

    Returns:
        tuple[Decimal, Decimal, Decimal]: 保有数量、平均取得単価、取得価格合計
    """
    logger.info(f"保有数量と取得価格の計算開始 user_id={user_id}, symbol={symbol}")
    # 購入トランザクションの集計（調整済み値を優先使用）
    logger.info(f"購入トランザクション集計開始 user_id={user_id}, symbol={symbol}")
    buy_query = select(
        func.sum(func.coalesce(models.Transaction.adjusted_quantity, models.Transaction.quantity)).label(
            "total_quantity"
        ),
        func.sum(
            func.coalesce(models.Transaction.adjusted_quantity, models.Transaction.quantity)
            * func.coalesce(models.Transaction.adjusted_price, models.Transaction.price)
        ).label("total_cost"),
    ).where(
        models.Transaction.user_id == user_id,
        models.Transaction.symbol == symbol,
        models.Transaction.transaction_type == "buy",
    )
    buy_result = await db.execute(buy_query)
    buy_data = buy_result.fetchone()
    total_buy_quantity = buy_data.total_quantity or 0
    total_buy_cost = buy_data.total_cost or 0

    # 売却トランザクションの集計（調整済み値を優先使用）
    logger.info(f"売却トランザクション集計開始 user_id={user_id}, symbol={symbol}")
    sell_query = select(
        func.sum(func.coalesce(models.Transaction.adjusted_quantity, models.Transaction.quantity))
    ).where(
        models.Transaction.user_id == user_id,
        models.Transaction.symbol == symbol,
        models.Transaction.transaction_type == "sell",
    )
    sell_result = await db.execute(sell_query)
    total_sell_quantity = sell_result.scalar() or 0

    # 現在の保有数量と平均取得単価を計算
    current_quantity = total_buy_quantity - total_sell_quantity
    average_cost = total_buy_cost / total_buy_quantity if total_buy_quantity > 0 else 0
    current_total_cost = current_quantity * average_cost

    return current_quantity, average_cost, current_total_cost


async def calculate_realized_pl_from_transactions(db: AsyncSession, user_id: int, symbol: str) -> Decimal:
    """
    売却取引の実現損益合計を取得する

    Args:
        db (AsyncSession): データベースセッション
        user_id (int): ユーザーID
        symbol (str): 銘柄コード

    Returns:
        Decimal: 売却取引の実現損益合計（該当がなければ0）
    """

    logger.info(f"売却の実現損益計算開始 user_id={user_id}, symbol={symbol}")
    realized_pl_query = select(func.sum(models.Transaction.realized_pl)).where(
        models.Transaction.user_id == user_id,
        models.Transaction.symbol == symbol,
        models.Transaction.transaction_type == "sell",
    )
    result = await db.execute(realized_pl_query)
    return result.scalar() or Decimal("0")


async def calculate_total_dividend_after_tax(db: AsyncSession, user_id: int, symbol: str) -> Decimal:
    """指定銘柄の配当総額（税・手数料控除後）を取得する

    Args:
        db (AsyncSession): データベースセッション
        user_id (int): ユーザーID
        symbol (str): 銘柄コード

    Returns:
        Decimal: 税・手数料控除後の配当総額（該当がなければ0）
    """

    logger.info(f"配当総額計算開始 user_id={user_id}, symbol={symbol}")
    dividend_query = select(
        func.sum(
            models.Dividend.total_amount
            - func.coalesce(models.Dividend.tax, 0)
            - func.coalesce(models.Dividend.fee, 0)
        )
    ).where(models.Dividend.user_id == user_id, models.Dividend.symbol == symbol)

    result = await db.execute(dividend_query)
    return result.scalar() or Decimal("0")


async def calculate_holding_pl(db: AsyncSession, holding: models.Holding) -> bool:
    """
    保有銘柄の損益情報を計算して更新する

    Args:
        db (AsyncSession): データベースセッション
        holding (models.Holding): 更新対象のホールディング

    Returns:
        bool: 更新に成功した場合は True、必要情報が不足した場合は False
    """
    logger.info(f"保有損益計算開始 user_id={holding.user_id}, symbol={holding.symbol}")
    # 銘柄情報を取得
    stock_query = select(models.Stock).where(models.Stock.symbol == holding.symbol)
    stock_result = await db.execute(stock_query)
    stock = stock_result.scalar_one_or_none()
    if not stock:
        return False

    # トランザクション履歴から最新の保有情報を取得
    new_quantity, new_average_cost, new_total_cost = await calculate_holding_from_transactions(
        db, holding.user_id, holding.symbol
    )

    # 保有情報を更新（数量、平均取得単価、取得価格合計のみ）
    holding.quantity = new_quantity
    holding.average_cost = new_average_cost
    holding.total_cost = new_total_cost

    # 実現損益をトランザクションから再集計
    holding.realized_pl = await calculate_realized_pl_from_transactions(db, holding.user_id, holding.symbol)

    # 配当総額を配当テーブルから再集計（税・手数料控除後）
    holding.total_dividend = await calculate_total_dividend_after_tax(db, holding.user_id, holding.symbol)

    # 現在値を取得
    current_price = await get_current_price(stock)
    if current_price > 0:
        holding.current_price = current_price
    elif current_price == 0 and holding.current_price is None:
        # 上場廃止などで株価が取得できない場合は0を設定
        holding.current_price = Decimal("0")

    # 現在値がない場合でも、初回取得時以外は既存の価格で計算を続行
    # 上場廃止銘柄でも実現損益と配当を反映するため、損益計算は必ず実行
    if holding.current_price is None:
        # 完全に価格情報がない初回のみスキップ
        return False

    # 時価評価額の計算
    holding.market_value = holding.current_price * holding.quantity

    # 評価損益の計算（実現損益と配当は既存の値を使用）
    holding.unrealized_pl = (
        holding.market_value
        + (holding.realized_pl or Decimal("0"))
        + (holding.total_dividend or Decimal("0"))
        - holding.total_cost
    )

    # 評価損益率の計算（取得価格が0の場合は0%とする）
    holding.unrealized_pl_percentage = (
        (holding.unrealized_pl / holding.total_cost * 100) if holding.total_cost > 0 else Decimal("0")
    )

    return True


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
    logger.info(f"保有損益更新開始 user_id={user_id}, symbol={symbol}")
    # 保有情報を取得
    holding_query = select(Holding).where(Holding.user_id == user_id, Holding.symbol == symbol)
    result = await db.execute(holding_query)
    holding = result.scalar_one_or_none()

    if not holding:
        return None

    # 損益情報を更新
    updated = await calculate_holding_pl(db, holding)
    if updated:
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
    logger.info(f"全保有損益更新開始 user_id={user_id}")
    # 保有銘柄一覧を取得
    holdings = await list_holdings(db, user_id)
    updated_holdings = []

    # 各銘柄を更新
    for holding in holdings:
        updated = await calculate_holding_pl(db, holding)
        if updated:
            updated_holdings.append(holding)

    # 一括でコミット
    await db.commit()

    # 更新後のデータをリフレッシュ
    for holding in updated_holdings:
        await db.refresh(holding)

    return updated_holdings


async def list_holdings(db: AsyncSession, user_id: int, symbol: str = None) -> List[Holding]:
    """
    ユーザーの保有銘柄一覧を銘柄名と共に取得します。
    symbolが指定された場合は、その銘柄の情報のみを返します。

    Args:
        db (AsyncSession): 非同期データベースセッション
        user_id (int): ユーザーID
        symbol (str, optional): 銘柄コード。指定された場合はその銘柄の情報のみを返します。

    Returns:
        List[Holding]: 銘柄名を含む保有銘柄情報のリスト
    """
    logger.info(f"保有銘柄一覧取得 user_id={user_id}, symbol={symbol}")
    query = (
        select(Holding, Stock.name)
        .join(Stock, Holding.symbol == Stock.symbol)
        .where(Holding.user_id == user_id)
    )

    # symbolが指定された場合は、条件を追加
    if symbol:
        query = query.where(Holding.symbol == symbol)

    result = await db.execute(query)
    holdings = []
    for row in result:
        holding = row[0]
        holding.stock_name = row[1]
        holdings.append(holding)
    return holdings
