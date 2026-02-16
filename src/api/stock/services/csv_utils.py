"""CSV処理用共通ユーティリティ

SBI証券からエクスポートしたCSVをパースする際に使用する
共通関数・定数を提供する。
"""

import unicodedata
from datetime import datetime

import pandas as pd
from loguru import logger

from ..utils.datetime import to_jst

# 投資信託名からシンボルへのマッピング
FUND_SYMBOL_MAP = {
    "eMAXIS Slim 全世界株式(オール・カントリー)": "JP90C000H1T1",
    "eMAXIS Slim 新興国株式インデックス": "JP90C000F7H5",
    "SBI・iシェアーズ・インド株式インデックス・ファンド": "JP90C000PZX1",
    "SBI・V・S&P500インデックス・ファンド": "JP90C000J569",
    "EXE-i グローバルサウス株式ファンド": "JP90C000Q3K5",
    "eMAXIS Slim 国内株式(TOPIX)": "JP90C000ENA9",
    "SBI・S・米国高配当株式ファンド(年4回決算型)": "JP90C000REE2",
    "ＳＢＩ・Ｓ・米国高配当株式ファンド(年４回決算型)": "JP90C000REE2",
    "ＳＢＩ・Ｓ・米国高配当株式ファンド（年４回決算型）": "JP90C000REE2",
    "eMAXIS Neo 自動運転": "JP90C000HR52",
}

# Unicode正規化済みのマッピング
NORMALIZED_FUND_MAP = {unicodedata.normalize("NFKC", k): v for k, v in FUND_SYMBOL_MAP.items()}


def is_empty(val) -> bool:
    """値が空かどうかを判定"""
    return pd.isna(val) or str(val).strip() in ["", "--", "nan", "None"]


def to_number(val, default: float = 0.0) -> float:
    """文字列を数値に変換"""
    if is_empty(val):
        return default
    return float(str(val).replace(",", ""))


def get_fund_symbol(fund_name: str) -> str | None:
    """ファンド名からシンボルを取得

    Unicode正規化を行い、全角/半角の表記揺れを吸収する。
    """
    key = unicodedata.normalize("NFKC", fund_name) if fund_name else ""
    return NORMALIZED_FUND_MAP.get(key)


def decode_csv_content(content: bytes) -> list[str]:
    """CSVバイト列をデコードして行リストを返す

    UTF-8とCP932のエンコーディングを自動検出する。

    Args:
        content: CSVファイルのバイト列

    Returns:
        list[str]: デコードされた行のリスト

    Raises:
        ValueError: エンコーディングが検出できない場合
    """
    for enc in ("utf-8", "cp932"):
        try:
            text = content.decode(enc)
            return text.splitlines(keepends=True)
        except UnicodeDecodeError:
            continue

    logger.error("CSVデコードエラー action=decode_csv error=unsupported_encoding")
    raise ValueError("CSVの文字コードがutf-8でもcp932でもありません")


def date_key(dt: datetime) -> str:
    """差分検出用の日付キーを生成

    タイムゾーン情報がある場合はJSTに変換してから日付文字列を返す。

    Args:
        dt: 日付時刻オブジェクト

    Returns:
        str: YYYY-MM-DD形式の日付文字列
    """
    if dt.tzinfo is None:
        return dt.strftime("%Y-%m-%d")
    return to_jst(dt).strftime("%Y-%m-%d")
