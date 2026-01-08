"""週間騰落率通知APIのテスト"""

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from stock.schemas import StockWeeklyPerformance
from stock.services.notification_service import _build_ranking_row
from stock.services.notification_service import WEEKLY_PERFORMANCE_COLOR_GREEN, WEEKLY_PERFORMANCE_COLOR_RED
from stock.services.weekly_performance_service import get_top_bottom_performers


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


class TestBuildRankingRow:
    """ランキング行ビルダー関数のユニットテスト"""

    def test_positive_change_rate_uses_green_color(self):
        """騰落率がプラスの場合、緑色が使用されること"""
        row = _build_ranking_row(
            rank=1,
            name="テスト株",
            symbol="TEST1",
            change_rate=Decimal("10.00"),
        )

        # 騰落率テキストが緑色であること
        change_rate_text = row["contents"][2]
        assert change_rate_text["color"] == WEEKLY_PERFORMANCE_COLOR_GREEN
        assert change_rate_text["text"] == "+10.00%"

    def test_negative_change_rate_uses_red_color(self):
        """騰落率がマイナスの場合、赤色が使用されること"""
        row = _build_ranking_row(
            rank=1,
            name="テスト株",
            symbol="TEST1",
            change_rate=Decimal("-5.50"),
        )

        # 騰落率テキストが赤色であること
        change_rate_text = row["contents"][2]
        assert change_rate_text["color"] == WEEKLY_PERFORMANCE_COLOR_RED
        assert change_rate_text["text"] == "-5.50%"


@pytest.mark.asyncio
async def test_excludes_zero_quantity_holdings(
    client, auth_token, setup_japanese_stock_data, create_transaction, mocker
):
    """保有数量が0の銘柄が除外されることを検証（API統合テスト）

    setup_japanese_stock_dataフィクスチャで8058の買付取引が登録済み。
    全株売却後、週間パフォーマンスAPIが保有数量0の銘柄を除外することを確認する。
    """
    # 全株売却（保有数量を0にする）
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

    # 株価取得関数をモック化（呼ばれないはず）
    mock_jp_prices = mocker.patch(
        "stock.services.weekly_performance_service.get_japan_stock_weekly_prices",
        new_callable=AsyncMock,
    )

    # 週間パフォーマンス通知APIを呼び出す
    mock_notification = mocker.patch(
        "stock.routes.portfolio.send_weekly_performance_notification",
        new_callable=AsyncMock,
    )
    mock_notification.return_value = True

    response = await client.post(
        "/api/v1/portfolio/weekly-performance-notify",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    # 保有数量0の銘柄は除外されるため空リスト
    assert data["top_performers"] == []
    assert data["bottom_performers"] == []
    # 株価取得関数は呼ばれない（保有銘柄がないため）
    mock_jp_prices.assert_not_called()


@pytest.mark.asyncio
async def test_calculates_change_rate_correctly(
    db_session, auth_token, setup_japanese_stock_data, setup_us_stock_data, mocker
):
    """騰落率が正しく計算されることを検証（サービス層のユニットテスト）

    setup_japanese_stock_dataとsetup_us_stock_dataフィクスチャで取引データが登録済み。
    calculate_weekly_performance関数を直接呼び出し、騰落率計算ロジックを検証する。
    """
    # auth_tokenフィクスチャで作成されたユーザーを取得
    from sqlalchemy import select

    from stock.models import User

    result = await db_session.execute(select(User).where(User.username == "testuser"))
    user = result.scalar_one()

    # 日本株の株価取得をモック化
    mock_jp_prices = mocker.patch(
        "stock.services.weekly_performance_service.get_japan_stock_weekly_prices",
        new_callable=AsyncMock,
    )
    mock_jp_prices.return_value = (Decimal("3300"), Decimal("3000"))  # 3000 -> 3300 (+10%)

    # 米国株の株価取得をモック化
    mock_us_prices = mocker.patch(
        "stock.services.weekly_performance_service.get_us_stock_weekly_prices",
        new_callable=AsyncMock,
    )
    mock_us_prices.return_value = (Decimal("216.324"), Decimal("240.36"))  # 240.36 -> 216.324 (-10%)

    # 週間パフォーマンスを計算
    from stock.services.weekly_performance_service import calculate_weekly_performance

    performances = await calculate_weekly_performance(db=db_session, user_id=user.user_id)

    # 2銘柄のパフォーマンスが返されること
    assert len(performances) == 2

    # 日本株の騰落率チェック
    jp_perf = next((p for p in performances if p.symbol == "8058"), None)
    assert jp_perf is not None
    assert jp_perf.change_rate == Decimal("10.00")
    assert jp_perf.latest_price == Decimal("3300")
    assert jp_perf.old_price == Decimal("3000")

    # 米国株の騰落率チェック
    us_perf = next((p for p in performances if p.symbol == "AAPL"), None)
    assert us_perf is not None
    assert us_perf.change_rate == Decimal("-10.00")
    assert us_perf.latest_price == Decimal("216.324")
    assert us_perf.old_price == Decimal("240.36")


@pytest.mark.asyncio
async def test_weekly_performance_notify_endpoint(
    client, auth_token, setup_japanese_stock_data, setup_us_stock_data, mocker
):
    """週間騰落率通知APIの統合テスト

    setup_japanese_stock_dataとsetup_us_stock_dataフィクスチャで取引データが登録済み。
    週間パフォーマンス通知APIが正しく動作することを確認する。

    期待する動作:
    - ステータスコード200
    - 正しいレスポンス構造
    - LINE通知が送信される
    """
    # 週間株価取得関数をモック化（外部APIへのアクセスを防ぐ）
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
