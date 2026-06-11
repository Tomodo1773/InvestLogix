"""配当金CSVインポート機能のテスト"""

from datetime import datetime

import pytest

from stock.services.dividend_csv_import_service import (
    ParsedDividend,
    detect_new_dividends,
    parse_dividend_csv_content,
)
from stock.utils.datetime import JST


class TestParseDividendCsvContent:
    """配当金CSVパース機能のテスト"""

    def test_parse_dividend_csv_stock(self):
        """株式配当金CSVのパーステスト"""
        csv_content = '''"受渡日","口座","商品","銘柄名","数量","受取額(税引後・円)"
"2024/03/15","特定","株式","三菱商事 8058","100","25000"'''

        dividends, errors = parse_dividend_csv_content(csv_content.encode("utf-8"))

        assert len(dividends) == 1
        assert len(errors) == 0

        div = dividends[0]
        assert div.symbol == "8058"
        assert div.name == "三菱商事 8058"
        assert div.shares_owned == 100.0
        assert div.total_amount == 25000.0
        assert div.payment_date == datetime(2024, 3, 15, tzinfo=JST)

    def test_parse_dividend_csv_fund(self):
        """投資信託分配金CSVのパーステスト"""
        csv_content = '''"受渡日","口座","商品","銘柄名","数量","受取額(税引後・円)"
"2024/06/15","NISA","投資信託","eMAXIS Slim 全世界株式(オール・カントリー)","50000","1500"'''

        dividends, errors = parse_dividend_csv_content(csv_content.encode("utf-8"))

        assert len(dividends) == 1
        assert len(errors) == 0

        div = dividends[0]
        assert div.symbol == "JP90C000H1T1"
        assert div.shares_owned == 5.0  # 50000万口 / 10000 = 5口
        assert div.payment_date == datetime(2024, 6, 15, tzinfo=JST)

    def test_skip_nomura_mrf(self):
        """野村MRFを除外するテスト"""
        csv_content = '''"受渡日","口座","商品","銘柄名","数量","受取額(税引後・円)"
"2024/03/15","特定","株式","野村MRF","100","10"'''

        dividends, errors = parse_dividend_csv_content(csv_content.encode("utf-8"))

        assert len(dividends) == 0

    def test_skip_unknown_symbol(self):
        """シンボル不明の銘柄をスキップするテスト"""
        csv_content = '''"受渡日","口座","商品","銘柄名","数量","受取額(税引後・円)"
"2024/03/15","特定","投資信託","未知のファンド","100","1000"'''

        dividends, errors = parse_dividend_csv_content(csv_content.encode("utf-8"))

        assert len(dividends) == 0
        assert len(errors) == 1
        assert "シンボル不明" in errors[0]

    def test_invalid_encoding(self):
        """不正なエンコーディングのテスト"""
        # UTF-8でもCP932でもデコードできない不正なバイト列
        csv_content = b"\x80\x81\xc0\xc1\xfe\xff"

        with pytest.raises(ValueError, match="CSVの文字コード"):
            parse_dividend_csv_content(csv_content)

    def test_no_header(self):
        """ヘッダーなしCSVのテスト"""
        csv_content = "2024/03/15,特定,株式,テスト株式".encode("utf-8")

        with pytest.raises(ValueError, match="ヘッダ行が見つかりませんでした"):
            parse_dividend_csv_content(csv_content)


class TestDetectNewDividends:
    """配当金差分検出機能のテスト"""

    def test_detect_new_dividends(self):
        """新規配当金の検出テスト"""
        # パース済み配当金
        parsed = [
            ParsedDividend(
                symbol="8058",
                name="三菱商事",
                payment_date=datetime(2024, 3, 15),
                shares_owned=100.0,
                total_amount=25000.0,
            ),
            ParsedDividend(
                symbol="9984",
                name="ソフトバンクグループ",
                payment_date=datetime(2024, 6, 15),
                shares_owned=50.0,
                total_amount=2200.0,
            ),
        ]

        # 既存配当金（モック）
        class MockDividend:
            def __init__(self, symbol, payment_date, shares_owned, total_amount):
                self.symbol = symbol
                self.payment_date = payment_date
                self.shares_owned = shares_owned
                self.total_amount = total_amount

        existing = [
            MockDividend(
                symbol="8058",
                payment_date=datetime(2024, 3, 15),
                shares_owned=100.0,
                total_amount=25000.0,
            )
        ]

        # 差分検出
        new_dividends = detect_new_dividends(parsed, existing)

        # 8058は既存なので除外され、9984のみ新規として検出される
        assert len(new_dividends) == 1
        assert new_dividends[0].symbol == "9984"

    def test_no_new_dividends(self):
        """新規配当金なしのテスト"""
        parsed = []
        existing = []

        new_dividends = detect_new_dividends(parsed, existing)

        assert len(new_dividends) == 0
