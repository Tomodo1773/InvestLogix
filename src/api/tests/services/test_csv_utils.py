"""CSV共通ユーティリティのテスト"""

from datetime import UTC, datetime

import pytest

from stock.services.csv_utils import (
    date_key,
    decode_csv_content,
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


class TestDecodeCsvContent:
    """decode_csv_content関数のテスト"""

    def test_utf8_content(self):
        content = "日本語,テスト\n1,2".encode()
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
        dt = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        result = date_key(dt)
        # UTCからJSTへ変換されるので、日付が変わる可能性がある
        assert result.startswith("2024-01-15")

    def test_aware_datetime(self):
        from zoneinfo import ZoneInfo

        jst = ZoneInfo("Asia/Tokyo")
        dt = datetime(2024, 1, 15, 23, 0, 0, tzinfo=jst)
        assert date_key(dt) == "2024-01-15"
