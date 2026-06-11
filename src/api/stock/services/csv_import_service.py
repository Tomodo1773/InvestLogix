"""CSV取引履歴インポートサービス

SBI証券からエクスポートした約定履歴CSVをパースし、
既存の取引履歴との差分を検出する機能を提供する。
"""

import io
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import pandas as pd
from loguru import logger

from ..utils.datetime import JST
from .csv_utils import date_key, decode_csv_content, get_fund_symbol, is_empty, parse_date, to_number


@dataclass
class ParsedTransaction:
    """CSVからパースされた取引データ"""

    symbol: str
    name: str
    transaction_type: str  # "買付" or "売却"
    quantity: float
    price: float | None
    usd_price: float | None
    account_type: str
    fee: float
    tax: float
    transaction_date: datetime
    settlement_currency: str | None = None

    def __key(self):
        """差分検出用のハッシュキー"""
        trade_date = date_key(self.transaction_date)
        # 外貨建て（usd_priceあり）の場合はUSD単価で比較する。
        # 円建てpriceは受渡金額/数量で計算されるためエクスポート時の為替レートに依存し変動する。
        price_key = (
            round(float(self.usd_price), 4) if self.usd_price is not None else round(float(self.price), 2)
        )
        return (
            self.symbol,
            self.transaction_type,
            trade_date,
            self.account_type,
            round(float(self.quantity), 4),
            price_key,
        )

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if not isinstance(other, ParsedTransaction):
            return NotImplemented
        return self.__key() == other.__key()


def parse_csv_content(content: bytes) -> tuple[list[ParsedTransaction], list[str]]:
    """CSVバイト列をパースして取引データのリストを返す

    Args:
        content: CSVファイルのバイト列

    Returns:
        tuple[list[ParsedTransaction], list[str]]: (パース済み取引リスト, エラーメッセージリスト)

    Raises:
        ValueError: CSVが不正な形式の場合
    """
    errors = []

    # エンコーディング自動検出してデコード
    lines = decode_csv_content(content)

    # ヘッダー行を検索
    header_index = next(
        (i for i, line in enumerate(lines) if line.startswith("約定日") or line.startswith("国内約定日")),
        None,
    )
    if header_index is None:
        logger.error("CSVヘッダー検出エラー action=parse_csv error=header_not_found")
        raise ValueError("CSV内に約定日または国内約定日ヘッダが見つかりませんでした")

    # 外貨建てCSVか円建てCSVかを判定
    is_foreign = lines[header_index].startswith("国内約定日")

    # ヘッダー行以降をDataFrameに読み込み
    df_raw = pd.read_csv(io.StringIO("".join(lines[header_index:])), dtype=str)

    if is_foreign:
        # カラム名を統一
        rename_map = {
            "国内約定日": "約定日",
            "銘柄名": "銘柄",
            "預り区分": "預り",
            "国内受渡日": "受渡日",
            "受渡金額": "受渡金額/決済損益",
        }
        df_raw.rename(columns=rename_map, inplace=True)

        # 外貨建ては手数料・税金情報がない
        df_raw["手数料/諸経費等"] = "0"
        df_raw["税額"] = "0"
        df_raw["is_foreign"] = True
    else:
        df_raw["is_foreign"] = False
        df_raw["通貨"] = "日本円"

    # 銘柄コードの抽出・正規化
    if is_foreign:
        # 外貨建て: 銘柄名から ticker を抽出
        def extract_ticker(name):
            if pd.isna(name):
                return ""
            match = re.search(r"\s([A-Z]+)\s*/\s*", str(name))
            return match.group(1) if match else ""

        df_raw["銘柄コード"] = df_raw["銘柄"].apply(extract_ticker)
    else:
        # 円建て: 銘柄コードから取得、投資信託はファンド名から変換
        df_raw["銘柄コード"] = df_raw["銘柄コード"].fillna("").astype(str)
        missing_code_mask = (df_raw["銘柄コード"] == "") | (df_raw["銘柄コード"] == "--")
        df_raw.loc[missing_code_mask, "銘柄コード"] = df_raw.loc[missing_code_mask, "銘柄"].map(
            get_fund_symbol
        )

    df_raw.rename(columns={"銘柄コード": "コード"}, inplace=True)

    # コードの正規化（.0除去など）
    def normalize_code(val, name):
        if is_empty(val):
            cand = get_fund_symbol(name)
            return cand if cand else ""
        code_str = str(val)
        code_str = code_str[:-2] if code_str.endswith(".0") else code_str
        return code_str

    df_raw["コード"] = df_raw.apply(lambda row: normalize_code(row["コード"], row["銘柄"]), axis=1)

    # 預り区分の正規化（スラッシュ除去）
    df_raw["預り"] = df_raw["預り"].apply(lambda x: str(x).replace("/", "").strip() if pd.notnull(x) else x)

    # 数値項目の変換
    df_raw["手数料/諸経費等"] = df_raw["手数料/諸経費等"].apply(lambda x: to_number(x, 0.0))
    df_raw["税額"] = df_raw["税額"].apply(lambda x: to_number(x, 0.0))
    df_raw["受渡金額/決済損益"] = df_raw["受渡金額/決済損益"].apply(to_number)
    df_raw["約定単価"] = df_raw["約定単価"].apply(to_number)

    # 数量の変換（投資信託は万口単位なので10000で割る）
    def parse_amount(row):
        qty = row["約定数量"]
        if is_empty(qty):
            return 0.0
        qty_float = float(str(qty).replace(",", ""))
        return qty_float / 10000 if str(row["取引"]).startswith("投信") else qty_float

    df_raw["約定数量"] = df_raw.apply(parse_amount, axis=1)

    # 外貨建ての場合、約定単価をドル価格として保存する。
    if is_foreign:
        df_raw["約定単価_dollar"] = df_raw["約定単価"]

        # 約定数量が0の行は除外（ゼロ除算防止）
        non_zero_qty_mask = df_raw["約定数量"] != 0
        zero_qty_rows = df_raw[~non_zero_qty_mask]
        if not zero_qty_rows.empty:
            logger.warning(
                "約定数量が0の外貨建て取引を{}件スキップします action=parse_csv",
                len(zero_qty_rows),
            )

        # 約定数量が0でない行のみ、円建て単価を計算
        df_raw = df_raw[non_zero_qty_mask].copy()

        def calculate_jpy_price(row):
            if row["通貨"] == "日本円":
                return row["受渡金額/決済損益"] / row["約定数量"]
            if row["通貨"] == "米国ドル":
                return None
            return None

        df_raw["約定単価"] = df_raw.apply(calculate_jpy_price, axis=1)
    else:
        df_raw["約定単価_dollar"] = None

    # 取引種別の正規化
    df_raw["取引"] = df_raw["取引"].apply(
        lambda x: (
            "買付"
            if x in ["株式現物買", "投信金額買付", "買付"]
            else "売却"
            if x in ["株式現物売", "投信金額解約", "投信口数解約", "売却"]
            else "形式外"
        )
    )

    # 日付の変換
    df_raw["約定日"] = df_raw["約定日"].apply(parse_date)

    # 必要なカラムのみ抽出
    sbi_data = df_raw[
        [
            "コード",
            "銘柄",
            "預り",
            "約定日",
            "取引",
            "約定数量",
            "約定単価",
            "約定単価_dollar",
            "手数料/諸経費等",
            "税額",
            "通貨",
        ]
    ].copy()
    sbi_data.columns = [
        "symbol",
        "name",
        "custody_type",
        "trade_date",
        "type",
        "amount",
        "price",
        "price_dollar",
        "fee",
        "tax",
        "settlement_currency",
    ]

    # 預り区分の表記統一
    sbi_data["custody_type"] = sbi_data["custody_type"].replace(
        {"NISA(成)": "NISA(成長投資枠)", "NISA(つ)": "NISA(つみたて投資枠)", "NISA": "NISA(成長投資枠)"}
    )

    # 数値の丸め
    sbi_data["amount"] = sbi_data["amount"].astype(float).round(4)
    sbi_data["price"] = sbi_data["price"].apply(lambda x: round(float(x), 2) if pd.notnull(x) else None)
    sbi_data["price_dollar"] = sbi_data["price_dollar"].apply(
        lambda x: round(float(x), 4) if pd.notnull(x) else None
    )

    # SBI CSVの日付は日本時間の日付として扱う
    sbi_data["trade_date"] = pd.to_datetime(sbi_data["trade_date"], format="%Y/%m/%d").dt.tz_localize(JST)

    # ParsedTransactionオブジェクトのリストに変換
    transactions = []
    for _, row in sbi_data.iterrows():
        # 形式外の取引やシンボルが取得できなかったものはスキップ
        if row["type"] == "形式外":
            errors.append(f"スキップ: 形式外の取引 - {row['name']}")
            continue
        if not row["symbol"] or pd.isna(row["symbol"]):
            errors.append(f"スキップ: シンボル不明 - {row['name']}")
            continue

        transactions.append(
            ParsedTransaction(
                symbol=str(row["symbol"]),
                name=str(row["name"]),
                transaction_type=row["type"],
                quantity=float(row["amount"]),
                price=float(row["price"]) if pd.notnull(row["price"]) else None,
                usd_price=float(row["price_dollar"]) if pd.notnull(row["price_dollar"]) else None,
                account_type=row["custody_type"],
                fee=float(row["fee"]),
                tax=float(row["tax"]),
                transaction_date=row["trade_date"],
                settlement_currency=str(row["settlement_currency"]),
            )
        )

    logger.info(
        "CSVパースが完了しました action=parse_csv parsed_count={} skipped_count={}",
        len(transactions),
        len(errors),
    )

    return transactions, errors


def apply_usdjpy_rates(
    parsed_transactions: list[ParsedTransaction], rates_by_date: dict[date, float]
) -> tuple[list[ParsedTransaction], list[str]]:
    """USD決済の外貨建て取引に円建て単価を補完する。"""
    converted_transactions = []
    errors = []

    for tx in parsed_transactions:
        if tx.price is not None:
            converted_transactions.append(tx)
            continue

        if tx.settlement_currency != "米国ドル" or tx.usd_price is None:
            errors.append(f"スキップ: 円建て単価を計算できません - {tx.name}")
            continue

        rate = _find_rate_on_or_before(tx.transaction_date.date(), rates_by_date)
        if rate is None:
            errors.append(f"スキップ: 為替レート不明 - {tx.name} ({date_key(tx.transaction_date)})")
            continue

        tx.price = round(tx.usd_price * rate, 2)
        converted_transactions.append(tx)

    return converted_transactions, errors


def _find_rate_on_or_before(target_date: date, rates_by_date: dict[date, float]) -> float | None:
    for days_back in range(8):
        rate = rates_by_date.get(target_date - timedelta(days=days_back))
        if rate is not None:
            return rate
    return None


def detect_new_transactions(
    parsed_transactions: list[ParsedTransaction], existing_transactions: list
) -> list[ParsedTransaction]:
    """パース済み取引と既存取引を比較して新規取引を抽出

    Args:
        parsed_transactions: CSVからパースした取引リスト
        existing_transactions: DBから取得した既存取引リスト（Transaction型）

    Returns:
        list[ParsedTransaction]: 新規取引のリスト
    """
    # 既存取引をParsedTransactionに変換してセット化
    existing_set = set()
    for tx in existing_transactions:
        # Enumか文字列かに対応
        tx_type = tx.transaction_type.value if hasattr(tx.transaction_type, "value") else tx.transaction_type
        acc_type = tx.account_type.value if hasattr(tx.account_type, "value") else tx.account_type

        existing_set.add(
            ParsedTransaction(
                symbol=tx.symbol,
                name="",  # 名前は比較に使わない
                transaction_type="買付" if tx_type == "buy" else "売却",
                quantity=tx.quantity,
                price=tx.price,
                usd_price=tx.usd_price,
                account_type=acc_type,
                fee=tx.fee,
                tax=tx.tax,
                transaction_date=tx.transaction_date,
            )
        )

    # 差分を計算
    parsed_set = set(parsed_transactions)
    diff_set = parsed_set - existing_set

    # UI側でのプレビュー順が毎回変わらないよう、日付等で順序を安定化
    new_transactions = sorted(
        diff_set,
        key=lambda tx: (
            tx.transaction_date,
            tx.symbol,
            tx.account_type,
            tx.transaction_type,
        ),
    )

    logger.info(
        "差分検出が完了しました action=detect_new_transactions new_count={} existing_count={} parsed_count={}",
        len(new_transactions),
        len(existing_transactions),
        len(parsed_transactions),
    )

    return new_transactions
