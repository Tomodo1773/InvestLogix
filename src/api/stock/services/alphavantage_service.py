import json

import requests

from ..database import settings


async def fetch_us_stock_overview(symbol: str) -> dict:
    api_key = settings.ALPHAVANTAGE_API_KEY
    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={api_key}"
    response = requests.get(url)
    data = json.loads(response.text)
    return data


async def fetch_us_stock_search(symbol: str) -> dict:
    api_key = settings.ALPHAVANTAGE_API_KEY
    url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={symbol}&apikey={api_key}"
    response = requests.get(url)
    data = json.loads(response.text)
    return data


async def fetch_usdjpy_rate() -> float | None:
    """
    Alpha Vantage APIを使用して現在のドル円レートを取得します

    Returns:
        float | None: 現在のドル円レート。エラーの場合はNone
    """
    api_key = settings.ALPHAVANTAGE_API_KEY
    url = (
        f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=USD&to_currency=JPY&apikey={api_key}"
    )
    response = requests.get(url)
    data = json.loads(response.text)
    try:
        return float(data["Realtime Currency Exchange Rate"]["5. Exchange Rate"])
    except (KeyError, ValueError):
        return None


if __name__ == "__main__":
    import asyncio

    async def main():
        symbol = "VYM"  # テスト用のシンボル
        details = await fetch_us_stock_overview(symbol)
        if not details:
            details = await fetch_us_stock_search(symbol)
        print(details)
        # ドル円レートのテスト
        rate = await fetch_usdjpy_rate()
        if rate:
            print(f"Current USD/JPY rate: {rate}")

    asyncio.run(main())
