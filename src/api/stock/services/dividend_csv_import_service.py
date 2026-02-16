"""配当金CSVインポートサービス

SBI証券からエクスポートした配当金・分配金CSVをパースし、
既存の配当金データとの差分を検出する機能を提供する。
"""

import io
import unicodedata
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
from loguru import logger

from .csv_utils import date_key, decode_csv_content, get_fund_symbol, is_empty, to_number


@dataclass
class ParsedDividend:
    """CSVからパースされた配当金データ"""

    symbol: str
    name: str
    payment_date: datetime
    shares_owned: float  # 投資信託は万口→口に変換済み
    total_amount: float  # 受取額（税引後・円）

    def __key(self):
        """差分検出用のハッシュキー"""
        payment_date_str = date_key(self.payment_date)
        return (
            self.symbol,
            payment_date_str,
            round(float(self.shares_owned), 4),
            round(float(self.total_amount), 2),
        )

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if not isinstance(other, ParsedDividend):
            return NotImplemented
        return self.__key() == other.__key()


def parse_dividend_csv_content(content: bytes) -> tuple[list[ParsedDividend], list[str]]:
    """配当金CSVバイト列をパースして配当金データのリストを返す

    Args:
        content: CSVファイルのバイト列

    Returns:
        tuple[list[ParsedDividend], list[str]]: (パース済み配当金リスト, エラーメッセージリスト)

    Raises:
        ValueError: CSVが不正な形式の場合
    """
    errors = []

    # エンコーディング自動検出してデコード
    lines = decode_csv_content(content)

    # ヘッダー行を検索（配当金CSV特有のヘッダー）
    header_index = next(
        (i for i, line in enumerate(lines) if line.strip().startswith('"受渡日","口座"')),
        None,
    )
    if header_index is None:
        logger.error("CSVヘッダー検出エラー action=parse_dividend_csv error=header_not_found")
        raise ValueError("CSV内に配当金データのヘッダ行が見つかりませんでした")

    # ヘッダー行以降をDataFrameに読み込み
    df = pd.read_csv(io.StringIO("".join(lines[header_index:])), dtype=str)
    logger.info("配当金CSVから{}件のデータを読み込みました action=parse_dividend_csv", len(df))

    # 野村MRFを除外
    df = df[df["銘柄名"].apply(lambda x: unicodedata.normalize("NFKC", str(x)) != "野村MRF")]

    # シンボルを抽出
    def extract_symbol(row) -> str:
        name = str(row["銘柄名"])
        product_type = str(row["商品"])

        if product_type == "投資信託":
            symbol = get_fund_symbol(name)
            return symbol if symbol else ""

        # 株式/ETFの場合: 銘柄名からティッカーを抽出
        normalized = unicodedata.normalize("NFKC", name)
        # "銘柄名 TICKER" の形式を想定
        if " " in normalized:
            return normalized.rsplit(" ", 1)[-1]
        return ""

    df["symbol"] = df.apply(extract_symbol, axis=1)

    # 数量の変換（投資信託は万口単位なので10000で割る）
    def parse_amount(row) -> float:
        qty_str = row["数量"]
        if is_empty(qty_str):
            return 0.0
        qty = float(str(qty_str).replace(",", ""))
        return qty / 10000 if row["商品"] == "投資信託" else qty

    df["shares_owned"] = df.apply(parse_amount, axis=1)

    # 受取額（税引後・円）を数値に変換
    df["total_amount"] = df["受取額(税引後・円)"].apply(lambda x: int(to_number(x)))

    # 受渡日を日付に変換
    df["payment_date"] = pd.to_datetime(df["受渡日"], format="%Y/%m/%d")

    # ParsedDividendオブジェクトのリストに変換
    dividends = []
    for _, row in df.iterrows():
        # シンボルが取得できなかったものはスキップ
        if not row["symbol"] or pd.isna(row["symbol"]):
            errors.append(f"スキップ: シンボル不明 - {row['銘柄名']}")
            continue

        dividends.append(
            ParsedDividend(
                symbol=str(row["symbol"]),
                name=str(row["銘柄名"]),
                payment_date=row["payment_date"],
                shares_owned=float(row["shares_owned"]),
                total_amount=float(row["total_amount"]),
            )
        )

    logger.info(
        "配当金CSVパースが完了しました action=parse_dividend_csv parsed_count={} skipped_count={}",
        len(dividends),
        len(errors),
    )

    return dividends, errors


def detect_new_dividends(
    parsed_dividends: list[ParsedDividend], existing_dividends: list
) -> list[ParsedDividend]:
    """パース済み配当金と既存配当金を比較して新規配当金を抽出

    Args:
        parsed_dividends: CSVからパースした配当金リスト
        existing_dividends: DBから取得した既存配当金リスト（Dividend型）

    Returns:
        list[ParsedDividend]: 新規配当金のリスト
    """
    # 既存配当金をParsedDividendに変換してセット化
    existing_set = set()
    for div in existing_dividends:
        existing_set.add(
            ParsedDividend(
                symbol=div.symbol,
                name="",  # 名前は比較に使わない
                payment_date=div.payment_date,
                shares_owned=div.shares_owned,
                total_amount=div.total_amount,
            )
        )

    # 差分を計算
    parsed_set = set(parsed_dividends)
    diff_set = parsed_set - existing_set

    # UI側でのプレビュー順が毎回変わらないよう、日付等で順序を安定化
    new_dividends = sorted(
        diff_set,
        key=lambda d: (d.payment_date, d.symbol),
    )

    logger.info(
        "配当金差分検出が完了しました action=detect_new_dividends new_count={} existing_count={} parsed_count={}",
        len(new_dividends),
        len(existing_dividends),
        len(parsed_dividends),
    )

    return new_dividends
