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


async def _fetch_mufg_nav(client: httpx.AsyncClient, symbol: str) -> float | None:
    """
    三菱UFJアセットマネジメントの公式「投信情報API」から基準価額を取得します。

    同社のファンド以外はHTTP 200のまま datasets が null で返るため、None を返します。
    """
    response = await client.get(f"https://developer.am.mufg.jp/fund_information_latest/isin_cd/{symbol}")
    response.raise_for_status()
    datasets = response.json()["datasets"]
    return float(datasets[0]["nav"]) if datasets else None


async def _fetch_toushin_lib_nav(client: httpx.AsyncClient, symbol: str) -> float:
    """投信総合検索ライブラリーのページから基準価額を取得します。取得できない場合は0"""
    response = await client.get(f"https://toushin-lib.fwg.ne.jp/FdsWeb/FDST030000?isinCd={symbol}")
    soup = BeautifulSoup(response.text, "html.parser")
    price_div = soup.find("span", class_="h3 font-weight-bold")

    if price_div and price_div.text:
        # カンマを除去して数値に変換
        return float(price_div.text.replace(",", "").replace("円", "").strip())
    return 0.0


async def get_fund_price(symbol: str) -> float:
    """
    投資信託の基準価額を取得します。

    投信総合検索ライブラリーは自動取得を禁止しているため、公式APIがある三菱UFJアセットマネジメントの
    ファンドはAPIから取得します。それ以外のファンドは代替の取得元が無いため、当面ライブラリーから取得します。

    Args:
        symbol (str): ISINコード

    Returns:
        float: 基準価額。取得できない場合は0
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            nav = await _fetch_mufg_nav(client, symbol)
            if nav is not None:
                return nav
            return await _fetch_toushin_lib_nav(client, symbol)

    except (httpx.HTTPError, ValueError, KeyError) as e:
        logger.error(
            "投資信託の基準価額取得に失敗しました action=external_io symbol={} error={}",
            symbol,
            str(e),
        )
        return 0.0


if __name__ == "__main__":
    import asyncio

    async def main():
        # テスト用のシンボル（EXE-i グローバルサウス株式ファンド）
        symbol = "JP90C000Q3K5"

        # 基準価額の取得テスト
        price = await get_fund_price(symbol)
        logger.info("基準価額を取得しました action=external_io symbol={} price={}", symbol, price)

        # 詳細情報の取得テスト
        await fetch_investment_trust_details(symbol)
        logger.info("投資信託の詳細情報を取得しました action=external_io symbol={}", symbol)

    asyncio.run(main())
