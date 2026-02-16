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
    "ＳＢＩ・Ｓ・米国高配当株式ファンド（年４回決算型）": "JP90C000REE2",
    "eMAXIS Neo 自動運転": "JP90C000HR52",
}

# Unicode正規化済みのマッピング
NORMALIZED_FUND_MAP = {unicodedata.normalize("NFKC", k): v for k, v in FUND_SYMBOL_MAP.items()}


def get_fund_symbol(fund_name: str) -> str | None:
    """ファンド名からシンボルを取得"""
    key = unicodedata.normalize("NFKC", fund_name) if fund_name else ""
    return NORMALIZED_FUND_MAP.get(key)


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
        payment_date_str = self._date_key(self.payment_date)
        return (
            self.symbol,
            payment_date_str,
            round(float(self.shares_owned), 4),
            round(float(self.total_amount), 2),
        )

    @staticmethod
    def _date_key(dt: datetime) -> str:
        if dt.tzinfo is None:
            return dt.strftime("%Y-%m-%d")
        return to_jst(dt).strftime("%Y-%m-%d")

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if not isinstance(other, ParsedDividend):
            return NotImplemented
        return self.__key() == other.__key()


def is_empty(val) -> bool:
    """値が空かどうかを判定"""
    return pd.isna(val) or str(val).strip() in ["", "--", "nan", "None"]


def to_number(val, default=0.0) -> float:
    """文字列を数値に変換"""
    if is_empty(val):
        return default
    return float(str(val).replace(",", ""))


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

    # エンコーディング自動検出
    for enc in ("utf-8", "cp932"):
        try:
            text = content.decode(enc)
            lines = text.splitlines(keepends=True)
            break
        except UnicodeDecodeError:
            continue
    else:
        logger.error("CSVデコードエラー action=parse_dividend_csv error=unsupported_encoding")
        raise ValueError("CSVの文字コードがutf-8でもcp932でもありません")

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

    元スクリプトの挙動を再現:
    - CSV内の重複行(同じキーを持つ行)は全て除外される
    - drop_duplicates(..., keep=False)と同じ挙動

    Args:
        parsed_dividends: CSVからパースした配当金リスト
        existing_dividends: DBから取得した既存配当金リスト（Dividend型）

    Returns:
        list[ParsedDividend]: 新規配当金のリスト
    """
    # ParsedDividendをDataFrameに変換
    parsed_df = pd.DataFrame([
        {
            "symbol": d.symbol,
            "name": d.name,
            "payment_date": d._date_key(d.payment_date),
            "shares_owned": round(float(d.shares_owned), 4),
            "total_amount": round(float(d.total_amount), 2),
        }
        for d in parsed_dividends
    ])

    # 既存配当金をDataFrameに変換
    existing_df = pd.DataFrame([
        {
            "symbol": div.symbol,
            "name": "",
            "payment_date": ParsedDividend._date_key(div.payment_date),
            "shares_owned": round(float(div.shares_owned), 4),
            "total_amount": round(float(div.total_amount), 2),
        }
        for div in existing_dividends
    ])

    # 比較用キー列
    key_cols = ["symbol", "payment_date", "shares_owned", "total_amount"]

    # 両方のDataFrameを結合
    concatenated = pd.concat([parsed_df, existing_df], ignore_index=True)

    # 重複を除外(keep=Falseで重複行を全削除)
    # これにより、CSV内の重複も既存DBとの重複も全て除外される
    filtered = concatenated.drop_duplicates(subset=key_cols, keep=False)

    # 空のDataFrameの場合は早期リターン
    if filtered.empty:
        logger.info(
            "配当金差分検出が完了しました action=detect_new_dividends new_count=0 existing_count={} parsed_count={}",
            len(existing_dividends),
            len(parsed_dividends),
        )
        return []

    # 元がParsedDividendだったもののみを抽出
    new_dividends_df = filtered[filtered["name"] != ""]

    # DataFrameからParsedDividendに変換
    new_dividends = []
    for _, row in new_dividends_df.iterrows():
        # 元のparsed_dividendsから対応するオブジェクトを検索
        for d in parsed_dividends:
            if (
                d.symbol == row["symbol"]
                and d._date_key(d.payment_date) == row["payment_date"]
                and round(float(d.shares_owned), 4) == row["shares_owned"]
                and round(float(d.total_amount), 2) == row["total_amount"]
            ):
                new_dividends.append(d)
                break

    # UI側でのプレビュー順が毎回変わらないよう、日付等で順序を安定化
    new_dividends = sorted(
        new_dividends,
        key=lambda d: (d.payment_date, d.symbol),
    )

    logger.info(
        "配当金差分検出が完了しました action=detect_new_dividends new_count={} existing_count={} parsed_count={}",
        len(new_dividends),
        len(existing_dividends),
        len(parsed_dividends),
    )

    return new_dividends
