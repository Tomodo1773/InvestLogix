"""
株価取得共通モジュール
日本株と米国株の株価データ取得を統一的に処理する
"""

import asyncio
from typing import Optional

from loguru import logger

from ..utils.datetime import get_date_range_for_api
from .jquants_service import get_jquants_client
from .tiingo_service import fetch_us_daily_prices_from_tiingo


async def fetch_japan_stock_prices(symbol: str, days_back: int = 7) -> list[dict]:
    """
    日本株の株価データを取得します。

    Args:
        symbol: 証券コード
        days_back: 取得する日数（デフォルト7日）

    Returns:
        株価データのリスト（日付昇順）。取得できない場合は空リスト
        各要素は {"Date": str, "O": float, "H": float, "L": float, "C": float, ...} 形式
    """
    try:
        start_date, end_date = get_date_range_for_api(days_back=days_back)
        prices = await get_jquants_client().get_prices(
            symbol=symbol, start_date=start_date, end_date=end_date
        )
        return prices or []
    except Exception as e:
        logger.error(
            "日本株の株価取得に失敗しました action=external_io symbol={} error={}",
            symbol,
            str(e),
        )
        return []


async def fetch_us_stock_prices(symbol: str, days_back: int = 7) -> list[dict]:
    """
    米国株の株価データを取得します。

    Args:
        symbol: ティッカーシンボル
        days_back: 取得する日数（デフォルト7日）

    Returns:
        株価データのリスト（日付昇順）。取得できない場合は空リスト
        各要素は {"date": str, "close": float, ...} 形式
    """
    try:
        start_date, end_date = get_date_range_for_api(days_back=days_back)
        prices = await asyncio.to_thread(
            fetch_us_daily_prices_from_tiingo,
            symbol,
            start_date,
            end_date,
        )
        return prices or []
    except Exception as e:
        logger.error(
            "米国株の株価取得に失敗しました action=external_io symbol={} error={}",
            symbol,
            str(e),
        )
        return []


def get_latest_japan_price(prices: list[dict]) -> Optional[float]:
    """
    日本株の株価リストから最新の終値を取得します。

    Args:
        prices: fetch_japan_stock_prices() の戻り値

    Returns:
        最新の終値。データがない場合はNone
    """
    if prices and len(prices) > 0:
        return float(prices[-1].get("C", 0))
    return None


def get_latest_us_price(prices: list[dict]) -> Optional[float]:
    """
    米国株の株価リストから最新の終値を取得します。

    Args:
        prices: fetch_us_stock_prices() の戻り値

    Returns:
        最新の終値。データがない場合はNone
    """
    if prices and len(prices) > 0:
        return float(prices[-1]["close"])
    return None
