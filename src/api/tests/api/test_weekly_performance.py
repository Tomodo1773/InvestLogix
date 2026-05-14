"""週間騰落率および統合LINE通知のテスト"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from stock.schemas import StockWeeklyPerformance
from stock.services.change_reason_service import ChangeReasonSections
from stock.services.notification_service import (
    WEEKLY_PERFORMANCE_COLOR_GREEN,
    WEEKLY_PERFORMANCE_COLOR_RED,
    _build_ranking_row,
    send_weekly_summary_notification,
)
from stock.services.weekly_performance_service import get_top_bottom_performers


class TestGetTopBottomPerformers:
    """get_top_bottom_performers関数のユニットテスト"""

    def test_with_more_than_5_performers(self):
        """5銘柄以上の場合、上位・下位5位が正しく抽出されること"""
        performances = [
            StockWeeklyPerformance(
                symbol=f"TEST{i}",
                name=f"Test Stock {i}",
                latest_price=100.0,
                old_price=100.0,
                change_rate=float(i - 5),  # -4, -3, -2, -1, 0, 1, 2, 3, 4, 5
            )
            for i in range(1, 11)
        ]

        top, bottom = get_top_bottom_performers(performances, n=5)

        # 上位5位のチェック（5, 4, 3, 2, 1）
        assert len(top) == 5
        assert top[0].change_rate == 5.0
        assert top[4].change_rate == 1.0

        # 下位5位のチェック（-4, -3, -2, -1, 0）
        assert len(bottom) == 5
        assert bottom[0].change_rate == -4.0
        assert bottom[4].change_rate == 0.0

    def test_with_less_than_5_performers(self):
        """5銘柄未満の場合、全銘柄が返されること"""
        performances = [
            StockWeeklyPerformance(
                symbol=f"TEST{i}",
                name=f"Test Stock {i}",
                latest_price=100.0,
                old_price=100.0,
                change_rate=float(i),
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
            change_rate=10.00,
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
            change_rate=-5.50,
        )

        # 騰落率テキストが赤色であること
        change_rate_text = row["contents"][2]
        assert change_rate_text["color"] == WEEKLY_PERFORMANCE_COLOR_RED
        assert change_rate_text["text"] == "-5.50%"


@pytest.mark.asyncio
async def test_excludes_zero_quantity_holdings(
    client, auth_token, setup_japanese_stock_data, create_transaction, mocker
):
    """保有数量が0の銘柄が除外されることを検証（GET API統合テスト）

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

    response = await client.get("/api/v1/portfolio/weekly-performance")
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
    mock_jp_prices.return_value = (3300.0, 3000.0)  # 3000 -> 3300 (+10%)

    # 米国株の株価取得をモック化
    mock_us_prices = mocker.patch(
        "stock.services.weekly_performance_service.get_us_stock_weekly_prices",
        new_callable=AsyncMock,
    )
    mock_us_prices.return_value = (216.324, 240.36)  # 240.36 -> 216.324 (-10%)

    # 週間パフォーマンスを計算
    from stock.services.weekly_performance_service import calculate_weekly_performance

    performances = await calculate_weekly_performance(db=db_session, user_id=user.user_id)

    # 2銘柄のパフォーマンスが返されること
    assert len(performances) == 2

    # 日本株の騰落率チェック
    jp_perf = next((p for p in performances if p.symbol == "8058"), None)
    assert jp_perf is not None
    assert jp_perf.change_rate == 10.00
    assert jp_perf.latest_price == 3300.0
    assert jp_perf.old_price == 3000.0

    # 米国株の騰落率チェック
    us_perf = next((p for p in performances if p.symbol == "AAPL"), None)
    assert us_perf is not None
    assert us_perf.change_rate == -10.00
    assert us_perf.latest_price == 216.324
    assert us_perf.old_price == 240.36


@pytest.mark.asyncio
async def test_get_weekly_performance_endpoint(
    client, auth_token, setup_japanese_stock_data, setup_us_stock_data, mocker
):
    """週間騰落率取得API（GET）の統合テスト

    setup_japanese_stock_dataとsetup_us_stock_dataフィクスチャで取引データが登録済み。
    画面表示用のGETエンドポイントが正しく動作することを確認する。
    """
    mock_jp_prices = mocker.patch(
        "stock.services.weekly_performance_service.get_japan_stock_weekly_prices",
        new_callable=AsyncMock,
    )
    mock_jp_prices.return_value = (3300.0, 3000.0)

    mock_us_prices = mocker.patch(
        "stock.services.weekly_performance_service.get_us_stock_weekly_prices",
        new_callable=AsyncMock,
    )
    mock_us_prices.return_value = (216.324, 240.36)

    response = await client.get("/api/v1/portfolio/weekly-performance")

    assert response.status_code == 200
    data = response.json()

    assert "top_performers" in data
    assert "bottom_performers" in data
    assert "all_performers" in data
    assert "timestamp" in data
    assert "notification_sent" not in data

    # 値上がり銘柄に日本株、値下がり銘柄に米国株が含まれること
    top_symbols = [p["symbol"] for p in data["top_performers"]]
    bottom_symbols = [p["symbol"] for p in data["bottom_performers"]]
    assert "8058" in top_symbols
    assert "AAPL" in bottom_symbols

    # all_performers には全銘柄が含まれること
    all_symbols = {p["symbol"] for p in data["all_performers"]}
    assert {"8058", "AAPL"}.issubset(all_symbols)


@pytest.mark.asyncio
async def test_send_weekly_summary_notification_combines_summary_and_rankings(monkeypatch, mocker):
    """資産サマリ・ランキング・AI解説が単一Flex Messageにまとまって送信される"""
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "dummy-token")

    mocker.patch(
        "stock.services.notification_service.NotificationService.get_line_user_id",
        new_callable=AsyncMock,
        return_value="U1234567890",
    )

    mock_line_response = MagicMock()
    mock_line_response.status_code = 200
    mock_post = mocker.patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=mock_line_response,
    )

    portfolio_data = {
        "total_cost": 1_000_000,
        "total_market_value": 1_200_000,
        "total_pl": 200_000,
        "total_pl_percentage": 20.0,
        "total_realized_pl": 50_000,
        "total_dividend": 30_000,
        "weekly_change": 15_000,
    }
    top = [
        StockWeeklyPerformance(
            symbol="7203", name="トヨタ自動車", latest_price=3300.0, old_price=3000.0, change_rate=10.0
        )
    ]
    bottom = [
        StockWeeklyPerformance(
            symbol="7974", name="任天堂", latest_price=6500.0, old_price=7000.0, change_rate=-7.14
        )
    ]
    sections = ChangeReasonSections(
        market_overview="今週は地合い改善。",
        top_commentary="トヨタ自動車は好決算で上昇。",
        bottom_commentary="任天堂はガイダンス下方修正で下落。",
    )

    result = await send_weekly_summary_notification(
        user_id=1,
        portfolio_data=portfolio_data,
        top_performers=top,
        bottom_performers=bottom,
        sections=sections,
        db=None,
    )

    assert result is True

    posted = mock_post.call_args.kwargs["json"]
    assert len(posted["messages"]) == 1
    assert posted["messages"][0]["type"] == "flex"

    body_json = json.dumps(posted["messages"][0]["contents"], ensure_ascii=False)
    # 資産サマリ
    assert "資産サマリ" in body_json
    assert "1,000,000円" in body_json
    assert "1,200,000円" in body_json
    assert "200,000円 (20.00%)" in body_json
    assert "+15,000円" in body_json
    # ランキング
    assert "上昇トップ5" in body_json
    assert "下落ワースト5" in body_json
    assert "トヨタ自動車" in body_json
    assert "任天堂" in body_json
    # AI解説
    assert "マーケット概況" in body_json
    assert "今週は地合い改善。" in body_json
    assert "トヨタ自動車は好決算で上昇。" in body_json
    assert "任天堂はガイダンス下方修正で下落。" in body_json
    # 旧固定コメントが含まれないこと
    assert "アドバイザーコメント" not in body_json


@pytest.mark.asyncio
async def test_send_weekly_summary_notification_works_without_sections(monkeypatch, mocker):
    """AI解説（sections=None）でも資産サマリとランキングだけで送信が成功する"""
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "dummy-token")

    mocker.patch(
        "stock.services.notification_service.NotificationService.get_line_user_id",
        new_callable=AsyncMock,
        return_value="U1234567890",
    )

    mock_line_response = MagicMock()
    mock_line_response.status_code = 200
    mock_post = mocker.patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=mock_line_response,
    )

    portfolio_data = {
        "total_cost": 500_000,
        "total_market_value": 480_000,
        "total_pl": -20_000,
        "total_pl_percentage": -4.0,
        "total_realized_pl": 0,
        "total_dividend": 1_000,
        "weekly_change": None,
    }
    top = [
        StockWeeklyPerformance(
            symbol="7203", name="トヨタ自動車", latest_price=3300.0, old_price=3000.0, change_rate=10.0
        )
    ]

    result = await send_weekly_summary_notification(
        user_id=1,
        portfolio_data=portfolio_data,
        top_performers=top,
        bottom_performers=[],
        sections=None,
        db=None,
    )

    assert result is True
    posted = mock_post.call_args.kwargs["json"]
    assert len(posted["messages"]) == 1
    assert posted["messages"][0]["type"] == "flex"

    body_json = json.dumps(posted["messages"][0]["contents"], ensure_ascii=False)
    assert "資産サマリ" in body_json
    assert "上昇トップ5" in body_json
    assert "下落ワースト5" in body_json
    # AI解説セクションが含まれないこと
    assert "マーケット概況" not in body_json
    # 前週比なしの場合、行自体が出ない
    assert "前週比" not in body_json
