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


if __name__ == "__main__":
    import asyncio

    async def main():
        symbol = "VYM"  # テスト用のシンボル
        details = await fetch_us_stock_overview(symbol)
        if not details:
            details = await fetch_us_stock_search(symbol)
        print(details)

    asyncio.run(main())
