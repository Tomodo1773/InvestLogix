"""日時のJST変換機能のテスト

ユーティリティ関数およびスキーマのシリアライズ/バリデーションが
正しくJSTを扱うことを検証します。
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from stock.schemas import Dividend, DividendBase, Transaction, TransactionCreate
from stock.utils.datetime import JST, UTC, from_jst_input, to_jst


class TestDatetimeUtils:
    """日時変換ユーティリティ関数のテスト"""

    def test_to_jst_with_utc_datetime(self):
        """UTC日時をJSTに変換できること"""
        utc_dt = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        jst_dt = to_jst(utc_dt)

        assert jst_dt.tzinfo == JST
        assert jst_dt.hour == 9  # UTC 0:00 = JST 9:00

    def test_to_jst_with_naive_datetime(self):
        """naive datetimeはUTCとして解釈されJSTに変換されること"""
        naive_dt = datetime(2024, 1, 1, 0, 0, 0)
        jst_dt = to_jst(naive_dt)

        assert jst_dt.tzinfo == JST
        assert jst_dt.hour == 9  # UTC 0:00 = JST 9:00

    def test_to_jst_with_jst_datetime(self):
        """JST日時はそのまま返されること"""
        jst_input = datetime(2024, 1, 1, 9, 0, 0, tzinfo=JST)
        jst_dt = to_jst(jst_input)

        assert jst_dt.tzinfo == JST
        assert jst_dt.hour == 9

    def test_to_jst_with_none(self):
        """Noneが入力された場合はNoneが返ること"""
        assert to_jst(None) is None

    def test_from_jst_input_with_naive_datetime(self):
        """naive datetimeはJSTとして解釈されること"""
        naive_dt = datetime(2024, 1, 1, 0, 0, 0)
        jst_dt = from_jst_input(naive_dt)

        assert jst_dt.tzinfo == JST
        assert jst_dt.hour == 0  # そのまま JST 0:00

    def test_from_jst_input_with_utc_datetime(self):
        """UTC日時はJSTに変換されること"""
        utc_dt = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        jst_dt = from_jst_input(utc_dt)

        assert jst_dt.tzinfo == JST
        assert jst_dt.hour == 9  # UTC 0:00 = JST 9:00

    def test_from_jst_input_with_none(self):
        """Noneが入力された場合はNoneが返ること"""
        assert from_jst_input(None) is None


class TestSchemaJSTSerialization:
    """スキーマのJSTシリアライズテスト"""

    def test_transaction_serializes_to_jst(self):
        """Transactionスキーマが日時をJST ISO形式でシリアライズすること"""
        # UTC日時を持つTransactionを作成
        utc_dt = datetime(2024, 1, 1, 15, 0, 0, tzinfo=UTC)
        transaction = Transaction(
            transaction_id=1,
            user_id=1,
            symbol="8058",
            transaction_type="buy",
            quantity=100,
            price=3000,
            account_type="NISA(成長投資枠)",
            fee=0,
            tax=0,
            transaction_date=utc_dt,
        )

        # シリアライズ結果を確認
        data = transaction.model_dump()
        # UTC 15:00 = JST 翌日 00:00
        assert data["transaction_date"] == "2024-01-02T00:00:00+09:00"

    def test_dividend_serializes_to_jst(self):
        """Dividendスキーマが日時をJST ISO形式でシリアライズすること"""
        # UTC日時を持つDividendを作成
        utc_dt = datetime(2024, 3, 14, 15, 0, 0, tzinfo=UTC)
        dividend = Dividend(
            dividend_id=1,
            user_id=1,
            symbol="8058",
            payment_date=utc_dt,
            shares_owned=100,
            total_amount=25000,
            tax=2500,
            fee=0,
        )

        # シリアライズ結果を確認
        data = dividend.model_dump()
        # UTC 15:00 = JST 翌日 00:00
        assert data["payment_date"] == "2024-03-15T00:00:00+09:00"


class TestSchemaJSTValidation:
    """スキーマのJSTバリデーションテスト"""

    def test_transaction_create_validates_naive_as_jst(self):
        """TransactionCreateがnaive datetimeをJSTとして解釈すること"""
        transaction = TransactionCreate(
            symbol="8058",
            transaction_type="buy",
            quantity=100,
            price=3000,
            account_type="NISA(成長投資枠)",
            fee=0,
            tax=0,
            transaction_date=datetime(2024, 1, 1, 9, 0, 0),  # naive datetime
        )

        # バリデーション後の値を確認
        assert transaction.transaction_date.tzinfo == JST
        assert transaction.transaction_date.hour == 9

    def test_dividend_base_validates_naive_as_jst(self):
        """DividendBaseがnaive datetimeをJSTとして解釈すること"""
        dividend = DividendBase(
            symbol="8058",
            payment_date=datetime(2024, 3, 15, 0, 0, 0),  # naive datetime
            shares_owned=100,
            total_amount=25000,
            tax=2500,
            fee=0,
        )

        # バリデーション後の値を確認
        assert dividend.payment_date.tzinfo == JST
        assert dividend.payment_date.hour == 0


class TestJSTBoundaryEdgeCases:
    """JSTタイムゾーン境界のエッジケーステスト"""

    def test_jst_midnight_converts_correctly(self):
        """JST 0:00 が正しく変換されること（UTC 15:00前日）"""
        # JST 2024-01-01 00:00:00
        jst_midnight = datetime(2024, 1, 1, 0, 0, 0, tzinfo=JST)

        # UTCに変換すると前日の15:00
        utc_equivalent = jst_midnight.astimezone(UTC)
        assert utc_equivalent.day == 31
        assert utc_equivalent.month == 12
        assert utc_equivalent.year == 2023
        assert utc_equivalent.hour == 15

    def test_month_boundary_jst(self):
        """月をまたぐJST境界が正しく処理されること"""
        # JST 2024-12-01 00:00:00 = UTC 2024-11-30 15:00:00
        jst_dec_first = datetime(2024, 12, 1, 0, 0, 0, tzinfo=JST)
        utc_equiv = jst_dec_first.astimezone(UTC)

        assert utc_equiv.month == 11
        assert utc_equiv.day == 30

        # to_jstで戻すと元の12月1日になること
        back_to_jst = to_jst(utc_equiv)
        assert back_to_jst.month == 12
        assert back_to_jst.day == 1

    def test_year_boundary_jst(self):
        """年をまたぐJST境界が正しく処理されること"""
        # JST 2024-01-01 00:00:00 = UTC 2023-12-31 15:00:00
        jst_new_year = datetime(2024, 1, 1, 0, 0, 0, tzinfo=JST)
        utc_equiv = jst_new_year.astimezone(UTC)

        assert utc_equiv.year == 2023
        assert utc_equiv.month == 12
        assert utc_equiv.day == 31

        # to_jstで戻すと元の2024年1月1日になること
        back_to_jst = to_jst(utc_equiv)
        assert back_to_jst.year == 2024
        assert back_to_jst.month == 1
        assert back_to_jst.day == 1
