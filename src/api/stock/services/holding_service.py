from typing import List, NamedTuple, Optional

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from ..models import Holding, Stock
from ..schemas import SecurityType
from ..services import alphavantage_service, investment_trust_service
from .stock_price_fetcher import (
    fetch_japan_stock_prices,
    fetch_us_stock_prices,
    get_latest_japan_price,
    get_latest_us_price,
)


class HoldingUpdateResult(NamedTuple):
    updated: bool
    price_fetch_failed: bool


async def get_japan_stock_price(symbol: str) -> float:
    """
    日本株の最新株価を取得します。

    Args:
        symbol (str): 証券コード

    Returns:
        float: 最新株価。取得できない場合は0
    """
    prices = await fetch_japan_stock_prices(symbol, days_back=7)
    price = get_latest_japan_price(prices)
    if price is not None:
        logger.info("日本株株価を取得しました symbol={} price={}", symbol, price)
        return price
    logger.info("日本株株価を取得できませんでした symbol={}", symbol)
    return 0.0


async def get_us_stock_price(symbol: str) -> float:
    """
    米国株・ETFの最新株価を円換算して取得します。

    Args:
        symbol (str): ティッカーシンボル

    Returns:
        float: 最新株価（円換算後）。取得できない場合は0
    """
    try:
        usdjpy_rate = await alphavantage_service.fetch_usdjpy_rate()
    except Exception as e:
        logger.warning("為替レート取得でエラーが発生しました symbol={} error={}", symbol, str(e))
        return 0.0

    if not usdjpy_rate:
        logger.info("為替レートが取得できませんでした symbol={}", symbol)
        return 0.0

    prices = await fetch_us_stock_prices(symbol, days_back=7)
    price = get_latest_us_price(prices)
    if price is not None:
        price_jpy = price * float(usdjpy_rate)
        logger.info("米国株株価を取得しました symbol={} price={}", symbol, price_jpy)
        return price_jpy

    logger.info("米国株株価を取得できませんでした symbol={}", symbol)
    return 0.0


async def get_current_price(stock: Stock) -> float:
    """
    証券種別と通貨に基づいて最新株価を取得します。
    日本株、米国株、米国ETF、投資信託に対応します。

    Args:
        stock (Stock): 銘柄情報

    Returns:
        float: 最新株価
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
    return 0.0


async def calculate_holding_from_transactions(
    db: AsyncSession,
    user_id: int,
    symbol: str,
):
    """
    トランザクション履歴から保有数量と取得価格を計算する
    株式分割がある場合は調整済み値を使用する

    Args:
        db (AsyncSession): データベースセッション
        user_id (int): ユーザーID
        symbol (str): 銘柄コード

    Returns:
        tuple[float, float, float]: 保有数量、平均取得単価、取得価格合計
    """
    # 購入トランザクションの集計（調整済み値を優先使用）
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
    total_buy_quantity = float(buy_data.total_quantity or 0)
    total_buy_cost = float(buy_data.total_cost or 0)

    # 売却トランザクションの集計（調整済み値を優先使用）
    sell_query = select(
        func.sum(func.coalesce(models.Transaction.adjusted_quantity, models.Transaction.quantity))
    ).where(
        models.Transaction.user_id == user_id,
        models.Transaction.symbol == symbol,
        models.Transaction.transaction_type == "sell",
    )
    sell_result = await db.execute(sell_query)
    total_sell_quantity = float(sell_result.scalar() or 0)

    # 現在の保有数量と平均取得単価を計算
    current_quantity = total_buy_quantity - total_sell_quantity
    average_cost = total_buy_cost / total_buy_quantity if total_buy_quantity > 0 else 0
    current_total_cost = current_quantity * average_cost

    logger.info(
        "Transactionを取得しました action=aggregate user_id={} symbol={} total_buy_quantity={} total_sell_quantity={}",
        user_id,
        symbol,
        total_buy_quantity,
        total_sell_quantity,
    )

    return current_quantity, average_cost, current_total_cost


async def calculate_realized_pl_from_transactions(
    db: AsyncSession,
    user_id: int,
    symbol: str,
) -> float:
    """
    売却取引の実現損益合計を取得する

    Args:
        db (AsyncSession): データベースセッション
        user_id (int): ユーザーID
        symbol (str): 銘柄コード

    Returns:
        float: 売却取引の実現損益合計（該当がなければ0）
    """

    realized_pl_query = select(func.sum(models.Transaction.realized_pl)).where(
        models.Transaction.user_id == user_id,
        models.Transaction.symbol == symbol,
        models.Transaction.transaction_type == "sell",
    )
    result = await db.execute(realized_pl_query)
    realized_pl = float(result.scalar() or 0)
    logger.info(
        "Transactionを取得しました action=aggregate user_id={} symbol={} realized_pl={}",
        user_id,
        symbol,
        realized_pl,
    )
    return realized_pl


async def calculate_total_dividend_after_tax(
    db: AsyncSession,
    user_id: int,
    symbol: str,
) -> float:
    """指定銘柄の配当総額（税・手数料控除後）を取得する

    Args:
        db (AsyncSession): データベースセッション
        user_id (int): ユーザーID
        symbol (str): 銘柄コード

    Returns:
        float: 税・手数料控除後の配当総額（該当がなければ0）
    """

    dividend_query = select(
        func.sum(
            models.Dividend.total_amount
            - func.coalesce(models.Dividend.tax, 0)
            - func.coalesce(models.Dividend.fee, 0)
        )
    ).where(models.Dividend.user_id == user_id, models.Dividend.symbol == symbol)

    result = await db.execute(dividend_query)
    total_dividend = float(result.scalar() or 0)
    logger.info(
        "Dividendを取得しました action=aggregate user_id={} symbol={} total_dividend={}",
        user_id,
        symbol,
        total_dividend,
    )
    return total_dividend


async def calculate_holding_pl(
    db: AsyncSession,
    holding: models.Holding,
) -> HoldingUpdateResult:
    """
    保有銘柄の損益情報を計算して更新する

    Args:
        db (AsyncSession): データベースセッション
        holding (models.Holding): 更新対象のホールディング

    Returns:
        HoldingUpdateResult: updated=損益計算まで進めたか、price_fetch_failed=価格取得が失敗扱いか
    """
    # 銘柄情報を取得
    stock_query = select(models.Stock).where(models.Stock.symbol == holding.symbol)
    stock_result = await db.execute(stock_query)
    stock = stock_result.scalar_one_or_none()
    if not stock:
        logger.info("Stockが見つかりませんでした action=select symbol={}", holding.symbol)
        return HoldingUpdateResult(updated=False, price_fetch_failed=True)
    logger.info(
        "Stockを取得しました action=select user_id={} symbol={} found=true",
        holding.user_id,
        holding.symbol,
    )

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
    price_fetch_failed = current_price <= 0
    if current_price > 0:
        holding.current_price = current_price
    elif current_price == 0 and holding.current_price is None:
        # 上場廃止などで株価が取得できない場合は0を設定
        holding.current_price = 0.0

    if price_fetch_failed:
        logger.warning(
            "価格取得に失敗しました action=price_fetch user_id={} symbol={}",
            holding.user_id,
            holding.symbol,
        )

    # 現在値がない場合でも、初回取得時以外は既存の価格で計算を続行
    # 上場廃止銘柄でも実現損益と配当を反映するため、損益計算は必ず実行
    if holding.current_price is None:
        # 完全に価格情報がない初回のみスキップ
        logger.info(
            "Holdingsの更新をスキップしました action=update symbol={} reason=no_current_price",
            holding.symbol,
        )
        return HoldingUpdateResult(updated=False, price_fetch_failed=True)

    # 時価評価額の計算
    holding.market_value = holding.current_price * holding.quantity

    # 含み損益（純粋な含み益のみ）
    holding.unrealized_pl = holding.market_value - holding.total_cost

    # 含み損益率
    holding.unrealized_pl_percentage = (
        (holding.unrealized_pl / holding.total_cost * 100) if holding.total_cost > 0 else 0.0
    )

    # 全体損益（含み益 + 実現損益 + 配当）
    holding.total_pl = holding.unrealized_pl + (holding.realized_pl or 0.0) + (holding.total_dividend or 0.0)

    # 全体損益率
    holding.total_pl_percentage = (
        (holding.total_pl / holding.total_cost * 100) if holding.total_cost > 0 else 0.0
    )

    return HoldingUpdateResult(updated=True, price_fetch_failed=price_fetch_failed)


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
    # 保有情報を取得
    holding_query = select(Holding).where(Holding.user_id == user_id, Holding.symbol == symbol)
    result = await db.execute(holding_query)
    holding = result.scalar_one_or_none()

    if not holding:
        logger.info("Holdingsが見つかりませんでした action=select user_id={} symbol={}", user_id, symbol)
        return None
    logger.info("Holdingsを取得しました action=select user_id={} symbol={} found=true", user_id, symbol)

    # 損益情報を更新
    result = await calculate_holding_pl(db, holding)
    if result.updated:
        await db.flush()
        await db.refresh(holding)
        logger.info("Holdingsを更新しました action=update user_id={} symbol={}", user_id, symbol)
    else:
        logger.info("Holdingsを更新できませんでした action=update user_id={} symbol={}", user_id, symbol)

    return holding


async def update_holding_note(
    db: AsyncSession, user_id: int, symbol: str, note: Optional[str]
) -> Optional[Holding]:
    """
    指定された銘柄のメモ（投資意図）を更新します。

    Args:
        db (AsyncSession): 非同期データベースセッション
        user_id (int): ユーザーID
        symbol (str): 銘柄コード
        note (Optional[str]): メモ本文。Noneでクリア

    Returns:
        Optional[Holding]: 更新後の保有情報。未保有銘柄の場合はNone
    """
    holdings = await list_holdings(db, user_id, symbol)
    if not holdings:
        logger.info("Holdingsが見つかりませんでした action=select user_id={} symbol={}", user_id, symbol)
        return None

    holding = holdings[0]
    holding.note = note
    await db.flush()
    logger.info("Holdingsのメモを更新しました action=update_note user_id={} symbol={}", user_id, symbol)
    return holding


async def update_all_holdings_pl(db: AsyncSession, user_id: int) -> tuple[List[Holding], List[str]]:
    """
    ユーザーの保有する全銘柄の損益を一括更新します。

    Args:
        db (AsyncSession): 非同期データベースセッション
        user_id (int): ユーザーID

    Returns:
        tuple[List[Holding], List[str]]:
            - 更新された保有情報のリスト
            - 価格取得に失敗した銘柄シンボルのリスト（ユーザ内ユニーク）
    """
    # 保有銘柄一覧を取得
    holdings = await list_holdings(db, user_id)
    updated_holdings = []
    failed_symbols: list[str] = []

    # 各銘柄を更新
    for holding in holdings:
        result = await calculate_holding_pl(db, holding)
        if result.updated:
            updated_holdings.append(holding)
        if result.price_fetch_failed and holding.symbol not in failed_symbols:
            failed_symbols.append(holding.symbol)

    # 一括でフラッシュ
    await db.flush()

    # 更新後のデータをリフレッシュ
    for holding in updated_holdings:
        await db.refresh(holding)

    logger.info(
        "Holdingsを更新しました action=bulk_update user_id={} holdings={} updated={} failed={}",
        user_id,
        len(holdings),
        len(updated_holdings),
        len(failed_symbols),
    )

    return updated_holdings, failed_symbols


async def list_holdings(db: AsyncSession, user_id: int, symbol: str = None) -> List[Holding]:
    """
    ユーザーの保有銘柄一覧を銘柄名、証券種別、通貨と共に取得します。
    symbolが指定された場合は、その銘柄の情報のみを返します。

    Args:
        db (AsyncSession): 非同期データベースセッション
        user_id (int): ユーザーID
        symbol (str, optional): 銘柄コード。指定された場合はその銘柄の情報のみを返します。

    Returns:
        List[Holding]: 銘柄名、証券種別、通貨を含む保有銘柄情報のリスト
    """
    query = (
        select(Holding, Stock.name, Stock.security_type, Stock.currency)
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
        holding.security_type = row[2]
        holding.currency = row[3]
        holdings.append(holding)
    logger.info(
        "Holdingsを取得しました action=select user_id={} symbol={} count={}",
        user_id,
        symbol,
        len(holdings),
    )
    return holdings
