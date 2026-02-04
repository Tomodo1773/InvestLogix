"""CSVインポート機能のテスト"""

from datetime import datetime

import pytest

from stock.schemas import AccountType, TransactionType
from stock.services.csv_import_service import ParsedTransaction, detect_new_transactions, parse_csv_content


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

    def test_parse_foreign_csv(self):
        """外貨建てCSVのパーステスト"""
        csv_content = """国内約定日,通貨,銘柄名,取引,預り区分,約定数量,約定単価,国内受渡日,受渡金額
2024/01/30,日本円,テスト株式 TEST / NASDAQ,買付,NISA,10,100,2024/02/01,15000"""

        transactions, errors = parse_csv_content(csv_content.encode("utf-8"))

        assert len(transactions) == 1
        assert len(errors) == 0

        tx = transactions[0]
        assert tx.symbol == "TEST"
        assert tx.transaction_type == "買付"
        assert tx.quantity == 10.0
        assert tx.usd_price == 100.0
        assert tx.account_type == "NISA(成長投資枠)"

    def test_parse_investment_trust(self):
        """投資信託CSVのパーステスト"""
        csv_content = """約定日,銘柄,銘柄コード,市場,取引,預り,課税,約定数量,約定単価,手数料/諸経費等,税額,受渡日,受渡金額/決済損益
2024/01/30,eMAXIS Slim 全世界株式(オール・カントリー),--,--,投信金額買付,NISA(つ),--,50000,20000,0,0,2024/02/01,100000000"""

        transactions, errors = parse_csv_content(csv_content.encode("utf-8"))

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

            def _create_enum(self, enum_class, value):
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
