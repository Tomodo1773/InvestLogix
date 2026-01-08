"""週間騰落率通知APIのテスト"""

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from stock.schemas import StockWeeklyPerformance
from stock.services.notification_service import _build_weekly_performance_message
from stock.services.weekly_performance_service import get_top_bottom_performers


@pytest_asyncio.fixture
async def setup_weekly_performance_test_data(client, auth_token, create_transaction):
    """週間騰落率テスト用データをセットアップするフィクスチャー

    Args:
        client: 非同期HTTPクライアント
        auth_token: 認証トークン
        create_transaction: 取引登録フィクスチャー

    Returns:
        dict: 取引情報
    """
    # 日本株の取引データ
    jp_transaction = {
        "symbol": "8058",
        "transaction_type": "buy",
        "quantity": "100.0",
        "price": "3000.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }
    jp_result = await create_transaction(jp_transaction)

    # 米国株の取引データ
    us_transaction = {
        "symbol": "AAPL",
        "transaction_type": "buy",
        "quantity": "10.0",
        "price": "36054",
        "usd_price": "240.36",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }
    us_result = await create_transaction(us_transaction)

    return {"jp": jp_result, "us": us_result}


class TestGetTopBottomPerformers:
    """get_top_bottom_performers関数のユニットテスト"""

    def test_with_more_than_5_performers(self):
        """5銘柄以上の場合、上位・下位5位が正しく抽出されること"""
        performances = [
            StockWeeklyPerformance(
                symbol=f"TEST{i}",
                name=f"Test Stock {i}",
                latest_price=Decimal("100"),
                old_price=Decimal("100"),
                change_rate=Decimal(str(i - 5)),  # -4, -3, -2, -1, 0, 1, 2, 3, 4, 5
            )
            for i in range(1, 11)
        ]

        top, bottom = get_top_bottom_performers(performances, n=5)

        # 上位5位のチェック（5, 4, 3, 2, 1）
        assert len(top) == 5
        assert top[0].change_rate == Decimal("5")
        assert top[4].change_rate == Decimal("1")

        # 下位5位のチェック（-4, -3, -2, -1, 0）
        assert len(bottom) == 5
        assert bottom[0].change_rate == Decimal("-4")
        assert bottom[4].change_rate == Decimal("0")

    def test_with_less_than_5_performers(self):
        """5銘柄未満の場合、全銘柄が返されること"""
        performances = [
            StockWeeklyPerformance(
                symbol=f"TEST{i}",
                name=f"Test Stock {i}",
                latest_price=Decimal("100"),
                old_price=Decimal("100"),
                change_rate=Decimal(str(i)),
            )
            for i in range(1, 4)  # 3銘柄
        ]

        top, bottom = get_top_bottom_performers(performances, n=5)

        assert len(top) == 3
        assert len(bottom) == 3

    def test_with_empty_list(self):
        """空のリストの場合、空のリストが返されること"""
        top, bottom = get_top_bottom_performers([], n=5)

        assert top == []
        assert bottom == []


class TestBuildWeeklyPerformanceMessage:
    """メッセージ作成関数のユニットテスト"""

    def test_message_format(self):
        """メッセージフォーマットが正しいこと"""
        top_performers = [
            StockWeeklyPerformance(
                symbol="TEST1",
                name="テスト株1",
                latest_price=Decimal("105"),
                old_price=Decimal("100"),
                change_rate=Decimal("5.00"),
            ),
        ]
        bottom_performers = [
            StockWeeklyPerformance(
                symbol="TEST2",
                name="テスト株2",
                latest_price=Decimal("95"),
                old_price=Decimal("100"),
                change_rate=Decimal("-5.00"),
            ),
        ]

        message = _build_weekly_performance_message(top_performers, bottom_performers)

        assert "📈 週間騰落ランキング" in message
        assert "【上昇トップ5】" in message
        assert "【下落ワースト5】" in message
        assert "テスト株1(TEST1): +5.00%" in message
        assert "テスト株2(TEST2): -5.00%" in message

    def test_message_with_empty_lists(self):
        """空のリストの場合、「データなし」と表示されること"""
        message = _build_weekly_performance_message([], [])

        assert "データなし" in message


@pytest.mark.asyncio
async def test_weekly_performance_notify_endpoint(
    client, auth_token, setup_weekly_performance_test_data, mocker
):
    """週間騰落率通知APIのテスト

    期待する動作:
    - ステータスコード200
    - 正しいレスポンス構造
    - 外部API（週間株価取得）がモック化されていること
    """
    # 週間株価取得関数をモック化
    mock_jp_prices = mocker.patch(
        "stock.services.weekly_performance_service.get_japan_stock_weekly_prices",
        new_callable=AsyncMock,
    )
    mock_jp_prices.return_value = (Decimal("3100"), Decimal("3000"))

    mock_us_prices = mocker.patch(
        "stock.services.weekly_performance_service.get_us_stock_weekly_prices",
        new_callable=AsyncMock,
    )
    mock_us_prices.return_value = (Decimal("250"), Decimal("240"))

    # LINE通知をモック化
    mock_notification = mocker.patch(
        "stock.routes.portfolio.send_weekly_performance_notification",
        new_callable=AsyncMock,
    )
    mock_notification.return_value = True

    # APIリクエスト実行
    response = await client.post(
        "/api/v1/portfolio/weekly-performance-notify",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    # レスポンスの検証
    assert response.status_code == 200
    data = response.json()

    # レスポンス構造のチェック
    assert "top_performers" in data
    assert "bottom_performers" in data
    assert "notification_sent" in data
    assert "timestamp" in data

    # 通知が送信されたこと
    assert data["notification_sent"] is True


@pytest.mark.asyncio
async def test_weekly_performance_excludes_zero_quantity(client, auth_token, create_transaction, mocker):
    """保有数量が0の銘柄が除外されることをテスト

    期待する動作:
    - 売却して保有数量が0になった銘柄は週間騰落率の計算対象から除外される
    """
    # 買付取引
    buy_transaction = {
        "symbol": "8058",
        "transaction_type": "buy",
        "quantity": "100.0",
        "price": "3000.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }
    await create_transaction(buy_transaction)

    # 全株売却
    sell_transaction = {
        "symbol": "8058",
        "transaction_type": "sell",
        "quantity": "100.0",
        "price": "3100.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-02-01T00:00:00",
    }
    await create_transaction(sell_transaction)

    # 週間株価取得関数をモック化（呼ばれないはず）
    mock_jp_prices = mocker.patch(
        "stock.services.weekly_performance_service.get_japan_stock_weekly_prices",
        new_callable=AsyncMock,
    )
    mock_jp_prices.return_value = (Decimal("3100"), Decimal("3000"))

    # LINE通知をモック化
    mock_notification = mocker.patch(
        "stock.routes.portfolio.send_weekly_performance_notification",
        new_callable=AsyncMock,
    )
    mock_notification.return_value = True

    # APIリクエスト実行
    response = await client.post(
        "/api/v1/portfolio/weekly-performance-notify",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    # レスポンスの検証
    assert response.status_code == 200
    data = response.json()

    # 保有数量0の銘柄は除外されるため、パフォーマンスリストは空
    assert data["top_performers"] == []
    assert data["bottom_performers"] == []

    # 株価取得関数は呼ばれていないこと
    mock_jp_prices.assert_not_called()
