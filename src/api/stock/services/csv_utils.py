"""CSV処理用共通ユーティリティ

SBI証券からエクスポートしたCSVをパースする際に使用する
共通関数・定数を提供する。
"""

from datetime import datetime

import pandas as pd
from loguru import logger

from ..utils.datetime import to_jst


def is_empty(val) -> bool:
    """値が空かどうかを判定"""
    return pd.isna(val) or str(val).strip() in ["", "--", "nan", "None"]


def to_number(val, default: float = 0.0) -> float:
    """文字列を数値に変換"""
    if is_empty(val):
        return default
    return float(str(val).replace(",", ""))


def parse_date(val) -> str | None:
    """日付文字列をYYYY/MM/DD形式に変換

    SBI証券CSVの複数日付形式に対応する。
    - YYYY年MM月DD日 形式（外貨建てCSV）
    - YYYY/MM/DD 形式（円建てCSV）
    """
    if is_empty(val):
        return None
    val_str = str(val).strip()
    if "年" in val_str:
        return pd.to_datetime(val_str, format="%Y年%m月%d日").strftime("%Y/%m/%d")
    return pd.to_datetime(val_str, format="%Y/%m/%d").strftime("%Y/%m/%d")


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
