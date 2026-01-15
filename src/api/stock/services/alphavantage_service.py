import json

import requests
from loguru import logger

from ..database import settings
from ..utils.cache import timed_cache


def _is_rate_limit_error(data: dict) -> bool:
    """
    Alpha Vantage APIのレート制限エラーを検出します

    Args:
        data (dict): APIレスポンス

    Returns:
        bool: レート制限エラーの場合True
    """
    return isinstance(data, dict) and "Information" in data and "API rate limit" in data["Information"]


async def fetch_us_stock_overview(symbol: str) -> dict:
    api_key = settings.ALPHAVANTAGE_API_KEY
    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={api_key}"
    logger.info(f"AlphaVantage API米国株概要情報取得開始 symbol={symbol}")
    try:
        response = requests.get(url)
        data = json.loads(response.text)
        if _is_rate_limit_error(data):
            logger.warning(f"AlphaVantage APIレート制限エラー symbol={symbol}")
            raise Exception("Alpha Vantage API rate limit exceeded")
        logger.info(f"AlphaVantage API米国株概要情報取得成功 symbol={symbol}")
        return data
    except Exception:
        logger.error(f"AlphaVantage API米国株概要情報取得エラー symbol={symbol}", exc_info=True)
        raise


async def fetch_us_stock_search(symbol: str) -> dict:
    api_key = settings.ALPHAVANTAGE_API_KEY
    url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={symbol}&apikey={api_key}"
    logger.info(f"AlphaVantage APIシンボル検索開始 symbol={symbol}")
    try:
        response = requests.get(url)
        data = json.loads(response.text)
        if _is_rate_limit_error(data):
            logger.warning(f"AlphaVantage APIレート制限エラー symbol={symbol}")
            raise Exception("Alpha Vantage API rate limit exceeded")
        logger.info(f"AlphaVantage APIシンボル検索成功 symbol={symbol}")
        return data
    except Exception:
        logger.error(f"AlphaVantage APIシンボル検索エラー symbol={symbol}", exc_info=True)
        raise


@timed_cache(seconds=3600)  # 1時間キャッシュ
async def fetch_usdjpy_rate() -> float | None:
    """
    Alpha Vantage APIを使用して現在のドル円レートを取得します
    レートリミット対策として1時間キャッシュします

    Returns:
        float | None: 現在のドル円レート。APIエラーの場合はNone

    Raises:
        Exception: レート制限に達した場合
    """
    api_key = settings.ALPHAVANTAGE_API_KEY
    url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=USD&to_currency=JPY&apikey={api_key}"
    logger.info("AlphaVantage API為替レート取得開始 pair=USD/JPY")
    try:
        response = requests.get(url)
        data = json.loads(response.text)
        if _is_rate_limit_error(data):
            logger.warning("AlphaVantage APIレート制限エラー pair=USD/JPY")
            raise Exception("Alpha Vantage API rate limit exceeded")
        rate = float(data["Realtime Currency Exchange Rate"]["5. Exchange Rate"])
        logger.info(f"AlphaVantage API為替レート取得成功 pair=USD/JPY, rate={rate}")
        return rate
    except (KeyError, ValueError, requests.RequestException):
        logger.error("AlphaVantage API為替レート取得エラー pair=USD/JPY", exc_info=True)
        return None


if __name__ == "__main__":
    import asyncio

    async def main():
        symbol = "VYM"  # テスト用のシンボル
        details = await fetch_us_stock_overview(symbol)
        if not details:
            details = await fetch_us_stock_search(symbol)
        # ドル円レートのテスト
        rate = await fetch_usdjpy_rate()
        if rate:
            print(f"Current USD/JPY rate: {rate}")

    asyncio.run(main())
