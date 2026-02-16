"""CSV共通ユーティリティのテスト"""

from datetime import datetime, timezone

import pytest

from stock.services.csv_utils import (
    FUND_SYMBOL_MAP,
    date_key,
    decode_csv_content,
    get_fund_symbol,
    is_empty,
    to_number,
)


class TestIsEmpty:
    """is_empty関数のテスト"""

    def test_empty_string(self):
        assert is_empty("") is True

    def test_whitespace_only(self):
        assert is_empty("   ") is True

    def test_none(self):
        assert is_empty(None) is True

    def test_double_dash(self):
        assert is_empty("--") is True

    def test_nan_string(self):
        assert is_empty("nan") is True

    def test_none_string(self):
        assert is_empty("None") is True

    def test_valid_value(self):
        assert is_empty("abc") is False

    def test_zero(self):
        assert is_empty(0) is False


class TestToNumber:
    """to_number関数のテスト"""

    def test_simple_number(self):
        assert to_number("123") == 123.0

    def test_number_with_comma(self):
        assert to_number("1,234,567") == 1234567.0

    def test_decimal(self):
        assert to_number("1,234.56") == 1234.56

    def test_empty_value(self):
        assert to_number("") == 0.0

    def test_empty_with_default(self):
        assert to_number("", default=99.9) == 99.9

    def test_none_value(self):
        assert to_number(None) == 0.0


class TestGetFundSymbol:
    """get_fund_symbol関数のテスト"""

    def test_exact_match(self):
        symbol = get_fund_symbol("eMAXIS Slim 全世界株式(オール・カントリー)")
        assert symbol == "JP90C000H1T1"

    def test_normalized_match(self):
        # 全角括弧のバリエーション
        symbol = get_fund_symbol("ＳＢＩ・Ｓ・米国高配当株式ファンド（年４回決算型）")
        assert symbol == "JP90C000REE2"

    def test_unknown_fund(self):
        symbol = get_fund_symbol("未知のファンド")
        assert symbol is None

    def test_empty_string(self):
        symbol = get_fund_symbol("")
        assert symbol is None


class TestDecodeCsvContent:
    """decode_csv_content関数のテスト"""

    def test_utf8_content(self):
        content = "日本語,テスト\n1,2".encode("utf-8")
        lines = decode_csv_content(content)
        assert len(lines) == 2
        assert "日本語" in lines[0]

    def test_cp932_content(self):
        content = "日本語,テスト\n1,2".encode("cp932")
        lines = decode_csv_content(content)
        assert len(lines) == 2
        assert "日本語" in lines[0]

    def test_invalid_encoding(self):
        # UTF-8でもCP932でもデコードできない不正なバイト列
        content = b"\x80\x81\xc0\xc1\xfe\xff"
        with pytest.raises(ValueError, match="CSVの文字コード"):
            decode_csv_content(content)


class TestDateKey:
    """date_key関数のテスト"""

    def test_naive_datetime(self):
        dt = datetime(2024, 1, 15)
        assert date_key(dt) == "2024-01-15"

    def test_utc_datetime(self):
        dt = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        result = date_key(dt)
        # UTCからJSTへ変換されるので、日付が変わる可能性がある
        assert result.startswith("2024-01-15")

    def test_aware_datetime(self):
        from zoneinfo import ZoneInfo

        jst = ZoneInfo("Asia/Tokyo")
        dt = datetime(2024, 1, 15, 23, 0, 0, tzinfo=jst)
        assert date_key(dt) == "2024-01-15"


class TestFundSymbolMap:
    """FUND_SYMBOL_MAPの検証"""

    def test_all_symbols_have_expected_format(self):
        """全シンボルがJPで始まることを確認"""
        for name, symbol in FUND_SYMBOL_MAP.items():
            assert symbol.startswith("JP"), f"{name}のシンボル{symbol}がJPで始まっていません"

    def test_sbi_fund_variants_map_to_same_symbol(self):
        """SBI米国高配当株式ファンドの各表記が同じシンボルにマッピングされることを確認"""
        expected_symbol = "JP90C000REE2"
        variants = [
            "SBI・S・米国高配当株式ファンド(年4回決算型)",
            "ＳＢＩ・Ｓ・米国高配当株式ファンド(年４回決算型)",
            "ＳＢＩ・Ｓ・米国高配当株式ファンド（年４回決算型）",
        ]
        for variant in variants:
            symbol = get_fund_symbol(variant)
            assert symbol == expected_symbol, f"{variant}が{expected_symbol}にマッピングされていません"
