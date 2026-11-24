"""投資信託の台帳

保有する投資信託ごとに、銘柄名と基準価額の取得元を手で管理する。
新しい投資信託を買ったら、ここに1件追加してからCSVを取り込む。

- name: SBI証券CSVでの銘柄名。CSV取込時の照合と、新規登録時の銘柄名に使う
- source: 基準価額の取得元
    - "mufg": 三菱UFJアセットマネジメントの公式「投信情報API」（ISINで引くため source_code は不要）
    - "sbi_am": SBIアセットマネジメントのファンド一覧（source_code はファンドページURL sa_XXXXXXXXXX.html の数字）
    - "nissay": ニッセイアセットマネジメントの基準価額一覧（source_code はサイトのファンド一覧JSONの fund-code）
"""

import unicodedata
from dataclasses import dataclass
from typing import Literal

FundSource = Literal["mufg", "sbi_am", "nissay"]


@dataclass(frozen=True)
class Fund:
    name: str
    source: FundSource
    source_code: str = ""

    def __post_init__(self) -> None:
        if self.source != "mufg" and not self.source_code:
            raise ValueError(f"source_code が未設定です: {self.name}")


FUNDS: dict[str, Fund] = {
    "JP90C000H1T1": Fund("eMAXIS Slim 全世界株式(オール・カントリー)", "mufg"),
    "JP90C000F7H5": Fund("eMAXIS Slim 新興国株式インデックス", "mufg"),
    "JP90C000ENC5": Fund("eMAXIS Slim 先進国株式インデックス", "mufg"),
    "JP90C000ENA9": Fund("eMAXIS Slim 国内株式(TOPIX)", "mufg"),
    "JP90C000HR52": Fund("eMAXIS Neo 自動運転", "mufg"),
    "JP90C000J569": Fund("SBI・V・S&P500インデックス・ファンド", "sbi_am", "2019092601"),
    "JP90C000PZX1": Fund("SBI・iシェアーズ・インド株式インデックス・ファンド", "sbi_am", "2023092202"),
    "JP90C000Q3K5": Fund("EXE-i グローバルサウス株式ファンド", "sbi_am", "2023102001"),
    "JP90C000REE2": Fund("SBI・S・米国高配当株式ファンド(年4回決算型)", "sbi_am", "2024122003"),
    "JP90C000BRT6": Fund("<購入・換金手数料なし>ニッセイTOPIXインデックスファンド", "nissay", "121526"),
}


def _normalize_name(name: str) -> str:
    """全角/半角と空白の表記揺れを吸収する"""
    return unicodedata.normalize("NFKC", name).replace(" ", "")


_SYMBOL_BY_NAME = {_normalize_name(fund.name): symbol for symbol, fund in FUNDS.items()}


def get_fund_symbol(fund_name: str) -> str | None:
    """SBI証券CSVの銘柄名から台帳のISINを引く。台帳に無ければNone"""
    return _SYMBOL_BY_NAME.get(_normalize_name(fund_name)) if fund_name else None
