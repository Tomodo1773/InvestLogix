from decimal import Decimal

import aiohttp
from bs4 import BeautifulSoup


async def fetch_investment_trust_details(symbol: str) -> dict:
    """
    投資信託の詳細情報を取得します。

    Args:
        symbol (str): ISINコード

    Returns:
        dict: 投資信託の詳細情報
    """
    url = f"https://toushin-lib.fwg.ne.jp/FdsWeb/FDST030000?isinCd={symbol}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()

    soup = BeautifulSoup(html, "html.parser")

    # 銘柄名を取得
    name_elem = soup.select_one("body > div:nth-of-type(4) > div > div > div:nth-of-type(1) > div:nth-of-type(1) > h3")
    name = name_elem.text.strip() if name_elem else None

    return {
        "name": name,
        "market": None,
        "industry": None,
    }


async def get_fund_price(symbol: str) -> Decimal:
    """
    投資信託の基準価額を取得します。

    Args:
        symbol (str): ISINコード

    Returns:
        Decimal: 基準価額。取得できない場合は0
    """
    url = f"https://toushin-lib.fwg.ne.jp/FdsWeb/FDST030000?isinCd={symbol}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                html = await response.text()

        soup = BeautifulSoup(html, "html.parser")
        price_div = soup.find("span", class_="h3 font-weight-bold")

        if price_div and price_div.text:
            # カンマを除去して数値に変換
            price_text = price_div.text.replace(",", "").replace("円", "").strip()
            return Decimal(price_text)

        return Decimal("0")

    except (aiohttp.ClientError, ValueError) as e:
        print(f"Error fetching fund price for {symbol}: {str(e)}")
        return Decimal("0")


if __name__ == "__main__":
    import asyncio

    async def main():
        # テスト用のシンボル（eMAXIS Slim 全世界株式(除く日本)）
        symbol = "JP90C000Q3K5"

        # 基準価額の取得テスト
        price = await get_fund_price(symbol)
        print(f"基準価額: {price}円")

        # 詳細情報の取得テスト
        details = await fetch_investment_trust_details(symbol)
        print("詳細情報:", details)

    asyncio.run(main())
