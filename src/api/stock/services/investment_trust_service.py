import httpx
from bs4 import BeautifulSoup
from loguru import logger


async def fetch_investment_trust_details(symbol: str) -> dict:
    """
    投資信託の詳細情報を取得します。

    Args:
        symbol (str): ISINコード

    Returns:
        dict: 投資信託の詳細情報
    """
    url = f"https://toushin-lib.fwg.ne.jp/FdsWeb/FDST030000?isinCd={symbol}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        html = response.text

    soup = BeautifulSoup(html, "html.parser")

    # 銘柄名を取得
    name_elem = soup.select_one(
        "body > div:nth-of-type(4) > div > div > div:nth-of-type(1) > div:nth-of-type(1) > h3"
    )
    name = name_elem.text.strip() if name_elem else None

    if not name:
        logger.error("投資信託の名前が取得できませんでした action=external_io symbol={}", symbol)
        raise ValueError(f"投資信託の名前が取得できませんでした: {symbol}")

    return {
        "name": name,
        "market": None,
        "industry": None,
    }


async def get_fund_price(symbol: str) -> float:
    """
    投資信託の基準価額を取得します。

    Args:
        symbol (str): ISINコード

    Returns:
        float: 基準価額。取得できない場合は0
    """
    url = f"https://toushin-lib.fwg.ne.jp/FdsWeb/FDST030000?isinCd={symbol}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            html = response.text

        soup = BeautifulSoup(html, "html.parser")
        price_div = soup.find("span", class_="h3 font-weight-bold")

        if price_div and price_div.text:
            # カンマを除去して数値に変換
            price_text = price_div.text.replace(",", "").replace("円", "").strip()
            return float(price_text)

        return 0.0

    except (httpx.HTTPError, ValueError) as e:
        logger.error(
            "投資信託の基準価額取得に失敗しました action=external_io symbol={} error={}",
            symbol,
            str(e),
        )
        return 0.0


if __name__ == "__main__":
    import asyncio

    async def main():
        # テスト用のシンボル（eMAXIS Slim 全世界株式(除く日本)）
        symbol = "JP90C000Q3K5"

        # 基準価額の取得テスト
        price = await get_fund_price(symbol)
        logger.info("基準価額を取得しました action=external_io symbol={} price={}", symbol, price)

        # 詳細情報の取得テスト
        await fetch_investment_trust_details(symbol)
        logger.info("投資信託の詳細情報を取得しました action=external_io symbol={}", symbol)

    asyncio.run(main())
