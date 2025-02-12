import requests
from bs4 import BeautifulSoup


async def fetch_investment_trust_details(symbol: str) -> dict:
    url = f"https://toushin-lib.fwg.ne.jp/FdsWeb/FDST030000?isinCd={symbol}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # 銘柄名を取得
    name_elem = soup.select_one("body > div:nth-of-type(4) > div > div > div:nth-of-type(1) > div:nth-of-type(1) > h3")
    name = name_elem.text.strip() if name_elem else None
    market = None
    industry = None

    return {
        "name": name,
        "market": market,
        "industry": industry,
    }


if __name__ == "__main__":
    import asyncio

    async def main():
        symbol = "JP90C000Q3K5"  # テスト用のシンボル
        details = await fetch_investment_trust_details(symbol)
        print(details)

    asyncio.run(main())
