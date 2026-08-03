"""株価取得共通モジュール

価格は price_history テーブルから読む。
- ダッシュボード経路: DB に無ければ失敗扱い（空リストを返す）
- 取引/配当登録経路: fallback_to_external=True を指定すると外部APIで補填し price_history に upsert する
"""

import asyncio
from datetime import date as date_type

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Stock
from ..schemas import SecurityType
from ..utils.datetime import get_date_range_for_api
from . import price_history_repo
from .jquants_service import get_jquants_client
from .tiingo_service import fetch_us_daily_prices_from_tiingo


async def fetch_japan_stock_prices(
    symbol: str,
    days_back: int = 7,
    *,
    db: AsyncSession,
    fallback_to_external: bool = False,
) -> list[dict]:
    """日本株の株価データを返す（DB引き、必要に応じて外部APIフォールバック）。

    Returns:
        日付昇順のリスト。各要素は {"Date": "YYYY-MM-DD", "O": float, "H": float,
        "L": float, "C": float, "Vo": int} 形式（C/O/H/L/Vo は調整済値）。
        取得できない場合は空リスト。
    """
    rows = await price_history_repo.get_recent_prices(db, symbol, days_back)
    if rows:
        return [_to_japan_shape(r) for r in rows]

    if not fallback_to_external:
        return []

    return await _fallback_japan_prices(db, symbol, days_back)


async def fetch_us_stock_prices(
    symbol: str,
    days_back: int = 7,
    *,
    db: AsyncSession,
    fallback_to_external: bool = False,
) -> list[dict]:
    """米国株の株価データを返す（DB引き、必要に応じて外部APIフォールバック）。

    Returns:
        日付昇順のリスト。各要素は {"date": "YYYY-MM-DD", "open": float, "high": float,
        "low": float, "close": float, "volume": int} 形式（すべて調整済値）。
        取得できない場合は空リスト。
    """
    rows = await price_history_repo.get_recent_prices(db, symbol, days_back)
    if rows:
        return [_to_us_shape(r) for r in rows]

    if not fallback_to_external:
        return []

    return await _fallback_us_prices(db, symbol, days_back)


async def refresh_price_history(db: AsyncSession, stock: Stock, days_back: int = 14) -> int:
    """指定銘柄の直近 days_back 日分の価格を外部APIから取得し price_history に upsert する。

    日次バッチ用。FUND（投資信託）はスキップする（基準価額のスポット取得のみで日次バーが無いため）。

    Returns:
        upsert した件数。FUND や対象外通貨は 0
    """
    if stock.security_type == SecurityType.FUND.value:
        return 0

    start_date, end_date = get_date_range_for_api(days_back=days_back)

    if stock.currency == "JPY":
        external = await get_jquants_client().get_prices(
            symbol=stock.symbol, start_date=start_date, end_date=end_date
        )
        normalized = [_from_jquants(row) for row in external]
    elif stock.currency == "USD":
        external = await asyncio.to_thread(
            fetch_us_daily_prices_from_tiingo, stock.symbol, start_date, end_date
        )
        normalized = [_from_tiingo(row) for row in external]
    else:
        return 0

    if not normalized:
        return 0

    await price_history_repo.upsert_prices(db, stock.symbol, normalized)
    return len(normalized)


def get_latest_japan_price(prices: list[dict]) -> float | None:
    """日本株の株価リストから最新終値（調整済）を取得"""
    if prices:
        return float(prices[-1].get("C", 0))
    return None


def get_latest_us_price(prices: list[dict]) -> float | None:
    """米国株の株価リストから最新終値（調整済）を取得"""
    if prices:
        return float(prices[-1]["close"])
    return None


async def _fallback_japan_prices(db: AsyncSession, symbol: str, days_back: int) -> list[dict]:
    """J-Quants から取得して price_history に upsert する（新規銘柄向けフォールバック）"""
    try:
        start_date, end_date = get_date_range_for_api(days_back=days_back)
        external = await get_jquants_client().get_prices(
            symbol=symbol, start_date=start_date, end_date=end_date
        )
        normalized = [_from_jquants(row) for row in external]
        if normalized:
            await price_history_repo.upsert_prices(db, symbol, normalized)
            await db.flush()
        logger.info(
            "日本株の株価をフォールバック取得しました action=external_io symbol={} count={}",
            symbol,
            len(normalized),
        )
        return [_to_japan_shape(r) for r in normalized]
    except Exception as e:
        logger.error(
            "日本株のフォールバック取得に失敗しました action=external_io symbol={} error={}",
            symbol,
            str(e),
        )
        return []


async def _fallback_us_prices(db: AsyncSession, symbol: str, days_back: int) -> list[dict]:
    """Tiingo から取得して price_history に upsert する（新規銘柄向けフォールバック）"""
    try:
        start_date, end_date = get_date_range_for_api(days_back=days_back)
        external = await asyncio.to_thread(fetch_us_daily_prices_from_tiingo, symbol, start_date, end_date)
        normalized = [_from_tiingo(row) for row in external]
        if normalized:
            await price_history_repo.upsert_prices(db, symbol, normalized)
            await db.flush()
        logger.info(
            "米国株の株価をフォールバック取得しました action=external_io symbol={} count={}",
            symbol,
            len(normalized),
        )
        return [_to_us_shape(r) for r in normalized]
    except Exception as e:
        logger.error(
            "米国株のフォールバック取得に失敗しました action=external_io symbol={} error={}",
            symbol,
            str(e),
        )
        return []


def _from_jquants(row: dict) -> dict:
    """J-Quants 生レスポンス → 内部 dict 形式（調整済値を抽出）"""
    return {
        "date": _parse_date(row["Date"]),
        "open": float(row["AdjO"]),
        "high": float(row["AdjH"]),
        "low": float(row["AdjL"]),
        "close": float(row["AdjC"]),
        "volume": int(row["AdjVo"]),
    }


def _from_tiingo(row: dict) -> dict:
    """Tiingo 整形済レスポンス → 内部 dict 形式"""
    return {
        "date": _parse_date(row["date"]),
        "open": float(row["open"]),
        "high": float(row["high"]),
        "low": float(row["low"]),
        "close": float(row["close"]),
        "volume": int(row["volume"]),
    }


def _to_japan_shape(row: dict) -> dict:
    """内部 dict → 日本株向け（J-Quants 風）形式"""
    return {
        "Date": _date_to_str(row["date"]),
        "O": row["open"],
        "H": row["high"],
        "L": row["low"],
        "C": row["close"],
        "Vo": row["volume"],
    }


def _to_us_shape(row: dict) -> dict:
    """内部 dict → 米国株向け（Tiingo 風）形式"""
    return {
        "date": _date_to_str(row["date"]),
        "open": row["open"],
        "high": row["high"],
        "low": row["low"],
        "close": row["close"],
        "volume": row["volume"],
    }


def _parse_date(value) -> date_type:
    if isinstance(value, date_type):
        return value
    return date_type.fromisoformat(str(value)[:10])


def _date_to_str(value) -> str:
    if isinstance(value, str):
        return value
    return value.strftime("%Y-%m-%d")
