import httpx
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
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
    data = response.json()
    if _is_rate_limit_error(data):
        raise Exception("Alpha Vantage API rate limit exceeded")
    return data


async def fetch_us_stock_search(symbol: str) -> dict:
    api_key = settings.ALPHAVANTAGE_API_KEY
    url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={symbol}&apikey={api_key}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
    data = response.json()
    if _is_rate_limit_error(data):
        raise Exception("Alpha Vantage API rate limit exceeded")
    return data


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
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
        data = response.json()
        if _is_rate_limit_error(data):
            raise Exception("Alpha Vantage API rate limit exceeded")
        return float(data["Realtime Currency Exchange Rate"]["5. Exchange Rate"])
    except (KeyError, ValueError, httpx.HTTPError):
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
            logger.info("USD/JPYのレートを取得しました action=external_io rate={}", rate)

    asyncio.run(main())
