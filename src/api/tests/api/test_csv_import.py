"""CSVインポート機能のテスト"""

from datetime import date
from datetime import datetime
from pathlib import Path

import pytest

from stock.schemas import AccountType, TransactionType
from stock.utils.datetime import JST
from stock.services.csv_import_service import (
    ParsedTransaction,
    apply_usdjpy_rates,
    detect_new_transactions,
    parse_csv_content,
)


class TestParseCsvContent:
    """CSVパース機能のテスト"""

    def test_parse_domestic_csv(self):
        """円建てCSVのパーステスト"""
        csv_content = """約定日,銘柄,銘柄コード,市場,取引,預り,課税,約定数量,約定単価,手数料/諸経費等,税額,受渡日,受渡金額/決済損益
2024/01/30,テスト株式,1234,東証,株式現物買,NISA(成),--,100,1000,0,0,2024/02/01,100000"""

        transactions, errors = parse_csv_content(csv_content.encode("utf-8"))

        assert len(transactions) == 1
        assert len(errors) == 0

        tx = transactions[0]
        assert tx.symbol == "1234"
        assert tx.name == "テスト株式"
        assert tx.transaction_type == "買付"
        assert tx.quantity == 100.0
        assert tx.price == 1000.0
        assert tx.usd_price is None
        assert tx.account_type == "NISA(成長投資枠)"
        assert tx.fee == 0.0
        assert tx.tax == 0.0
        assert tx.transaction_date == datetime(2024, 1, 30, tzinfo=JST)

    def test_parse_foreign_csv(self):
        """外貨建てCSVのパーステスト（実際のSBI証券フォーマット: YYYY年MM月DD日形式）"""
        csv_content = """国内約定日,通貨,銘柄名,取引,預り区分,約定数量,約定単価,国内受渡日,受渡金額
"2024年01月30日",日本円,テスト株式 TEST / NASDAQ,買付,NISA,10,100,24/02/01,15000"""

        transactions, errors = parse_csv_content(csv_content.encode("utf-8"))

        assert len(transactions) == 1
        assert len(errors) == 0

        tx = transactions[0]
        assert tx.symbol == "TEST"
        assert tx.transaction_type == "買付"
        assert tx.quantity == 10.0
        assert tx.price == 1500.0
        assert tx.usd_price == 100.0
        assert tx.account_type == "NISA(成長投資枠)"
        assert tx.transaction_date == datetime(2024, 1, 30, tzinfo=JST)

    def test_parse_foreign_usd_settlement_csv(self):
        """外貨決済の米国株CSVはUSD単価を保持し、円建て単価は未補完にする"""
        csv_content = """国内約定日,通貨,銘柄名,取引,預り区分,約定数量,約定単価,国内受渡日,受渡金額
"2024年01月30日",米国ドル,テスト株式 TEST / NASDAQ,買付,NISA,10,100,24/02/01,1000"""

        transactions, errors = parse_csv_content(csv_content.encode("utf-8"))

        assert len(transactions) == 1
        assert len(errors) == 0

        tx = transactions[0]
        assert tx.symbol == "TEST"
        assert tx.quantity == 10.0
        assert tx.price is None
        assert tx.usd_price == 100.0
        assert tx.settlement_currency == "米国ドル"

    def test_apply_usdjpy_rates(self):
        """外貨決済の米国株取引に約定日の為替で円建て単価を補完する"""
        transactions = [
            ParsedTransaction(
                symbol="TEST",
                name="テスト株式 TEST / NASDAQ",
                transaction_type="買付",
                quantity=10.0,
                price=None,
                usd_price=100.0,
                account_type="NISA(成長投資枠)",
                fee=0.0,
                tax=0.0,
                transaction_date=datetime(2024, 1, 30),
                settlement_currency="米国ドル",
            )
        ]

        converted, errors = apply_usdjpy_rates(transactions, {date(2024, 1, 30): 150.25})

        assert len(errors) == 0
        assert converted[0].price == 15025.0

    def test_apply_usdjpy_rates_uses_previous_rate(self):
        """約定日の為替がない場合は直前日の為替で円建て単価を補完する"""
        transactions = [
            ParsedTransaction(
                symbol="TEST",
                name="テスト株式 TEST / NASDAQ",
                transaction_type="買付",
                quantity=10.0,
                price=None,
                usd_price=100.0,
                account_type="NISA(成長投資枠)",
                fee=0.0,
                tax=0.0,
                transaction_date=datetime(2024, 1, 30),
                settlement_currency="米国ドル",
            )
        ]

        converted, errors = apply_usdjpy_rates(transactions, {date(2024, 1, 29): 149.5})

        assert len(errors) == 0
        assert converted[0].price == 14950.0

    def test_apply_usdjpy_rates_skips_when_rate_missing(self):
        """為替が取れない外貨決済行はスキップする"""
        transactions = [
            ParsedTransaction(
                symbol="TEST",
                name="テスト株式 TEST / NASDAQ",
                transaction_type="買付",
                quantity=10.0,
                price=None,
                usd_price=100.0,
                account_type="NISA(成長投資枠)",
                fee=0.0,
                tax=0.0,
                transaction_date=datetime(2024, 1, 30),
                settlement_currency="米国ドル",
            )
        ]

        converted, errors = apply_usdjpy_rates(transactions, {})

        assert converted == []
        assert len(errors) == 1
        assert "為替レート不明" in errors[0]

    def test_unsupported_foreign_currency_is_not_treated_as_jpy_price(self):
        """未対応通貨の外貨建てCSVは約定単価を円単価として扱わない"""
        csv_content = """国内約定日,通貨,銘柄名,取引,預り区分,約定数量,約定単価,国内受渡日,受渡金額
"2024年01月30日",ユーロ,テスト株式 TEST / NASDAQ,買付,NISA,10,100,24/02/01,1000"""

        transactions, errors = parse_csv_content(csv_content.encode("utf-8"))
        converted, rate_errors = apply_usdjpy_rates(transactions, {})

        assert len(errors) == 0
        assert converted == []
        assert len(rate_errors) == 1
        assert "円建て単価を計算できません" in rate_errors[0]

    def test_parse_sample_foreign_csv(self):
        """サンプルの外貨建てCSVを標準CSVとしてパースできる"""
        sample_path = Path(__file__).parents[4] / "samples" / "sbi_export_file" / "yakujo20260201135112.csv"

        transactions, errors = parse_csv_content(sample_path.read_bytes())

        assert len(errors) == 0
        assert len(transactions) == 13
        assert any(tx.settlement_currency == "米国ドル" for tx in transactions)

    def test_parse_investment_trust(self):
        """投資信託CSVのパーステスト"""
        csv_content = """約定日,銘柄,銘柄コード,市場,取引,預り,課税,約定数量,約定単価,手数料/諸経費等,税額,受渡日,受渡金額/決済損益
2024/01/30,eMAXIS Slim 全世界株式(オール・カントリー),--,--,投信金額買付,NISA(つ),--,50000,20000,0,0,2024/02/01,100000000"""

        transactions, _ = parse_csv_content(csv_content.encode("utf-8"))

        assert len(transactions) == 1
        tx = transactions[0]
        assert tx.symbol == "JP90C000H1T1"
        assert tx.quantity == 5.0  # 50000万口 / 10000 = 5口

    def test_skip_invalid_transaction(self):
        """形式外の取引をスキップするテスト"""
        csv_content = """約定日,銘柄,銘柄コード,市場,取引,預り,課税,約定数量,約定単価,手数料/諸経費等,税額,受渡日,受渡金額/決済損益
2024/01/30,テスト株式,1234,東証,配当金受取,特定,--,0,0,0,0,2024/02/01,1000"""

        transactions, errors = parse_csv_content(csv_content.encode("utf-8"))

        assert len(transactions) == 0
        assert len(errors) == 1
        assert "形式外の取引" in errors[0]

    def test_invalid_encoding(self):
        """不正なエンコーディングのテスト"""
        # UTF-8でもCP932でもデコードできない不正なバイト列
        # 0x80はCP932で未定義、0xC0-0xC1はUTF-8で無効
        csv_content = b"\x80\x81\xc0\xc1\xfe\xff"

        with pytest.raises(ValueError, match="CSVの文字コード"):
            parse_csv_content(csv_content)

    def test_no_header(self):
        """ヘッダーなしCSVのテスト"""
        csv_content = "2024/01/30,テスト株式,1234".encode("utf-8")

        with pytest.raises(ValueError, match="ヘッダが見つかりませんでした"):
            parse_csv_content(csv_content)


class TestDetectNewTransactions:
    """差分検出機能のテスト"""

    def test_detect_new_transactions(self):
        """新規取引の検出テスト"""
        # パース済み取引
        parsed = [
            ParsedTransaction(
                symbol="1234",
                name="テスト株式",
                transaction_type="買付",
                quantity=100.0,
                price=1000.0,
                usd_price=None,
                account_type="NISA(成長投資枠)",
                fee=0.0,
                tax=0.0,
                transaction_date=datetime(2024, 1, 30),
            ),
            ParsedTransaction(
                symbol="5678",
                name="テスト株式2",
                transaction_type="買付",
                quantity=50.0,
                price=2000.0,
                usd_price=None,
                account_type="特定",
                fee=100.0,
                tax=10.0,
                transaction_date=datetime(2024, 2, 1),
            ),
        ]

        # 既存取引（モック）
        class MockTransaction:
            def __init__(
                self, symbol, transaction_type, quantity, price, account_type, fee, tax, transaction_date
            ):
                self.symbol = symbol
                self.transaction_type = self._create_enum(TransactionType, transaction_type)
                self.quantity = quantity
                self.price = price
                self.usd_price = None
                self.account_type = self._create_enum(AccountType, account_type)
                self.fee = fee
                self.tax = tax
                self.transaction_date = transaction_date

            def _create_enum(self, _enum_class, value):
                class EnumValue:
                    def __init__(self, v):
                        self.value = v

                return EnumValue(value)

        existing = [
            MockTransaction(
                symbol="1234",
                transaction_type="buy",
                quantity=100.0,
                price=1000.0,
                account_type="NISA(成長投資枠)",
                fee=0.0,
                tax=0.0,
                transaction_date=datetime(2024, 1, 30),
            )
        ]

        # 差分検出
        new_transactions = detect_new_transactions(parsed, existing)

        # 1234は既存なので除外され、5678のみ新規として検出される
        assert len(new_transactions) == 1
        assert new_transactions[0].symbol == "5678"

    def test_no_new_transactions(self):
        """新規取引なしのテスト"""
        parsed = []
        existing = []

        new_transactions = detect_new_transactions(parsed, existing)

        assert len(new_transactions) == 0

    def test_foreign_price_change_not_detected_as_new(self):
        """外貨建て取引で円建てpriceが変わっても登録済みと判断されるテスト

        外貨建てCSVの円建てprice（受渡金額/数量）はエクスポートごとに変わるため、
        usd_priceが同じなら同一取引として判断する必要がある。
        """
        # 最初のエクスポートでインポートした取引（円建てprice=73063.0）
        parsed = [
            ParsedTransaction(
                symbol="MSFT",
                name="マイクロソフト",
                transaction_type="買付",
                quantity=1.0,
                price=73063.0,  # 新しいエクスポートでは為替が変わり別の値になる
                usd_price=477.535,
                account_type="NISA(成長投資枠)",
                fee=0.0,
                tax=0.0,
                transaction_date=datetime(2026, 1, 28),
            ),
        ]

        class MockTransaction:
            def __init__(
                self,
                symbol,
                transaction_type,
                quantity,
                price,
                usd_price,
                account_type,
                fee,
                tax,
                transaction_date,
            ):
                self.symbol = symbol
                self.transaction_type = transaction_type  # 文字列で渡す（DBの実際の返り値を模倣）
                self.quantity = quantity
                self.price = price
                self.usd_price = usd_price
                self.account_type = account_type
                self.fee = fee
                self.tax = tax
                self.transaction_date = transaction_date

        # DBには以前の為替レートで計算されたprice（72000.0）で保存済み
        existing = [
            MockTransaction(
                symbol="MSFT",
                transaction_type="buy",
                quantity=1.0,
                price=72000.0,  # 以前のエクスポートで登録された価格（為替レートが違う）
                usd_price=477.535,  # USD単価は変わらない
                account_type="NISA(成長投資枠)",
                fee=0.0,
                tax=0.0,
                transaction_date=datetime(2026, 1, 28),
            )
        ]

        new_transactions = detect_new_transactions(parsed, existing)

        # USD単価が同じなので登録済みと判断され、差分なし
        assert len(new_transactions) == 0
