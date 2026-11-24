"""
投資信託の基準価額を、台帳（fund_master）に書いた取得元から取得します。

投信総合検索ライブラリーは自動取得を禁止しているため使わず、各運用会社から取得します。
三菱UFJアセットマネジメント以外は公式APIが無いため、サイトが画面表示に使っているデータを読みます。
"""

import json
import re
from collections.abc import Awaitable, Callable

import httpx
from loguru import logger

from .fund_master import FUNDS, Fund

MUFG_FUND_API_URL = "https://developer.am.mufg.jp/fund_information_latest/isin_cd/{symbol}"
SBI_AM_FUND_LIST_URL = "https://apl.wealthadvisor.jp/webasp/sbi_am/pc/fund.aspx"
NISSAY_NAV_URL = "https://www.nam.co.jp/fundinfo/data/s_djson.php"


async def _fetch_mufg_nav(client: httpx.AsyncClient, symbol: str, fund: Fund) -> float:
    """三菱UFJアセットマネジメントの公式「投信情報API」から基準価額を取得します。"""
    response = await client.get(MUFG_FUND_API_URL.format(symbol=symbol))
    response.raise_for_status()
    # 同社のファンド以外はHTTP 200のまま datasets が null で返る
    datasets = response.json()["datasets"]
    if not datasets or datasets[0]["nav"] is None:
        raise ValueError("投信情報APIに基準価額がありません")
    return float(datasets[0]["nav"])


async def _fetch_sbi_am_nav(client: httpx.AsyncClient, symbol: str, fund: Fund) -> float:
    """SBIアセットマネジメントのファンド一覧ページに埋め込まれたJSONから基準価額を取得します。"""
    response = await client.get(SBI_AM_FUND_LIST_URL)
    response.raise_for_status()
    match = re.search(r"result\s*=\s*\{", response.text)
    if not match:
        raise ValueError("ファンド一覧のデータが見つかりません")
    data, _ = json.JSONDecoder().raw_decode(response.text, match.end() - 1)
    for row in data["fundlist"]:
        if row["msFundCode"] == fund.source_code:
            return float(row["kijyunkagaku"].replace(",", ""))
    raise ValueError(f"ファンド一覧にコード {fund.source_code} がありません")


async def _fetch_nissay_nav(client: httpx.AsyncClient, symbol: str, fund: Fund) -> float:
    """ニッセイアセットマネジメントの基準価額一覧データ（JSONP）から基準価額を取得します。"""
    response = await client.post(NISSAY_NAV_URL, data={"jsonname": "s_dkijun1.json"})
    response.raise_for_status()
    text = response.text
    data = json.loads(text[text.index("(") + 1 : text.rindex(")")])
    for node in data["result"]["nodes"]:
        if node["a_fcode"] == fund.source_code:
            return float(node["a_kj_003"])
    raise ValueError(f"基準価額一覧にコード {fund.source_code} がありません")


_FETCHERS: dict[str, Callable[[httpx.AsyncClient, str, Fund], Awaitable[float]]] = {
    "mufg": _fetch_mufg_nav,
    "sbi_am": _fetch_sbi_am_nav,
    "nissay": _fetch_nissay_nav,
}


async def get_fund_price(symbol: str) -> float:
    """
    投資信託の基準価額を取得します。

    Args:
        symbol (str): ISINコード

    Returns:
        float: 基準価額。取得できない場合は0
    """
    fund = FUNDS.get(symbol)
    if fund is None:
        logger.error("投資信託が台帳に未登録です action=external_io symbol={}", symbol)
        return 0.0

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            return await _FETCHERS[fund.source](client, symbol, fund)
    except (httpx.HTTPError, ValueError, KeyError) as e:
        logger.error(
            "投資信託の基準価額取得に失敗しました action=external_io symbol={} source={} error={}",
            symbol,
            fund.source,
            str(e),
        )
        return 0.0
