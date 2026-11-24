"""
投資信託の銘柄名と基準価額を取得します。

投信総合検索ライブラリーは自動取得を禁止しているため、公式APIがある三菱UFJアセットマネジメントの
ファンドはAPIから取得します。それ以外のファンドは代替の取得元が無いため、当面ライブラリーから取得します。
"""

import httpx
from bs4 import BeautifulSoup
from loguru import logger

MUFG_FUND_API_URL = "https://developer.am.mufg.jp/fund_information_latest/isin_cd/{symbol}"
TOUSHIN_LIB_URL = "https://toushin-lib.fwg.ne.jp/FdsWeb/FDST030000?isinCd={symbol}"


async def _fetch_mufg_fund(client: httpx.AsyncClient, symbol: str) -> dict | None:
    """
    三菱UFJアセットマネジメントの公式「投信情報API」からファンド情報を取得します。

    同社のファンド以外はHTTP 200のまま datasets が null で返るため、None を返します。
    APIの障害で同社以外のファンドの取得まで止めないよう、取得失敗もログを残して None を返します。
    """
    try:
        response = await client.get(MUFG_FUND_API_URL.format(symbol=symbol))
        response.raise_for_status()
        datasets = response.json()["datasets"]
    except (httpx.HTTPError, ValueError, KeyError) as e:
        logger.warning(
            "三菱UFJ投信情報APIの取得に失敗しました action=external_io symbol={} error={}", symbol, str(e)
        )
        return None
    return datasets[0] if datasets else None


async def _fetch_toushin_lib_page(client: httpx.AsyncClient, symbol: str) -> BeautifulSoup:
    """投信総合検索ライブラリーのファンド詳細ページを取得します。"""
    response = await client.get(TOUSHIN_LIB_URL.format(symbol=symbol))
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


async def fetch_investment_trust_details(symbol: str) -> dict:
    """
    投資信託の詳細情報を取得します。

    Args:
        symbol (str): ISINコード

    Returns:
        dict: 投資信託の詳細情報
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        fund = await _fetch_mufg_fund(client, symbol)
        if fund:
            name = fund.get("fund_name")
        else:
            soup = await _fetch_toushin_lib_page(client, symbol)
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
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            fund = await _fetch_mufg_fund(client, symbol)
            if fund and fund.get("nav") is not None:
                return float(fund["nav"])
            soup = await _fetch_toushin_lib_page(client, symbol)

        price_span = soup.find("span", class_="h3 font-weight-bold")
        if not (price_span and price_span.text):
            raise ValueError("基準価額の要素がページに見つかりません")
        # カンマを除去して数値に変換
        return float(price_span.text.replace(",", "").replace("円", "").strip())

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
        # テスト用のシンボル（EXE-i グローバルサウス株式ファンド）
        symbol = "JP90C000Q3K5"

        # 基準価額の取得テスト
        price = await get_fund_price(symbol)
        logger.info("基準価額を取得しました action=external_io symbol={} price={}", symbol, price)

        # 詳細情報の取得テスト
        await fetch_investment_trust_details(symbol)
        logger.info("投資信託の詳細情報を取得しました action=external_io symbol={}", symbol)

    asyncio.run(main())
