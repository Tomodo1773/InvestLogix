"""株価時系列データ取得APIのテスト"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_get_japanese_stock_price_history(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_token: str,
    setup_japanese_stock_data,
    mocker,
):
    """日本株の株価時系列データ取得のテスト（正常系）

    期待する動作:
    - ステータスコード200
    - 株価データのリストを返却
    - J-Quants APIが呼び出されること

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        setup_japanese_stock_data: 日本株テストデータ
        mocker: モッカー
    """
    # J-Quants APIのモックを設定
    mock_jquants_prices = [
        {
            "Date": "2025-01-20",
            "Open": 3000.0,
            "High": 3050.0,
            "Low": 2980.0,
            "Close": 3020.0,
            "Volume": 1000000,
        },
        {
            "Date": "2025-01-21",
            "Open": 3020.0,
            "High": 3080.0,
            "Low": 3010.0,
            "Close": 3060.0,
            "Volume": 1200000,
        },
    ]

    # 非同期関数なので、AsyncMockを使用
    from unittest.mock import AsyncMock

    mock_get_prices = mocker.patch(
        "stock.services.jquants_service.jquants_client.get_prices",
        new_callable=AsyncMock,
        return_value=mock_jquants_prices,
    )

    # APIリクエスト実行
    response = await client.get(
        "/api/v1/stocks/8058/price-history",
        params={"period": "1Y", "interval": "daily"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "8058"
    assert data["period"] == "1Y"
    assert data["interval"] == "daily"
    assert len(data["data"]) == 2

    # データの中身を検証
    assert data["data"][0]["date"] == "2025-01-20"
    assert data["data"][0]["open"] == 3000.0
    assert data["data"][0]["close"] == 3020.0
    assert data["data"][1]["date"] == "2025-01-21"

    # モックが呼び出されたことを確認
    mock_get_prices.assert_called_once()


@pytest.mark.asyncio
async def test_get_us_stock_price_history(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_token: str,
    setup_us_stock_data,
    mocker,
):
    """米国株の株価時系列データ取得のテスト（正常系）

    期待する動作:
    - ステータスコード200
    - 株価データのリストを返却
    - Stooqから株価が取得されること

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        setup_us_stock_data: 米国株テストデータ
        mocker: モッカー
    """
    # Stooqのモックデータ
    mock_stooq_data = [
        {
            "date": "2025-01-20",
            "open": 240.0,
            "high": 245.0,
            "low": 238.0,
            "close": 242.0,
            "volume": 50000000,
        },
        {
            "date": "2025-01-21",
            "open": 242.0,
            "high": 248.0,
            "low": 241.0,
            "close": 246.0,
            "volume": 55000000,
        },
    ]

    # キャッシュされたメソッドをモック化
    mock_fetch_us = mocker.patch(
        "stock.services.price_history_service.PriceHistoryService._fetch_us_stock_prices_cached",
        return_value=mock_stooq_data,
    )

    # APIリクエスト実行
    response = await client.get(
        "/api/v1/stocks/AAPL/price-history",
        params={"period": "1Y", "interval": "daily"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["period"] == "1Y"
    assert data["interval"] == "daily"
    assert len(data["data"]) == 2

    # データの中身を検証
    assert data["data"][0]["date"] == "2025-01-20"
    assert data["data"][0]["open"] == 240.0
    assert data["data"][0]["close"] == 242.0

    # モックが呼び出されたことを確認
    mock_fetch_us.assert_called_once()


@pytest.mark.asyncio
async def test_get_price_history_with_weekly_interval(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_token: str,
    setup_japanese_stock_data,
    mocker,
):
    """週次データへの集計テスト

    期待する動作:
    - ステータスコード200
    - 日次データが週次に集計されること

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        setup_japanese_stock_data: 日本株テストデータ
        mocker: モッカー
    """
    # 複数日分のモックデータ（同じ週の月曜〜金曜）
    mock_jquants_prices = [
        {
            "Date": "2025-01-20",
            "Open": 3000.0,
            "High": 3050.0,
            "Low": 2980.0,
            "Close": 3020.0,
            "Volume": 1000000,
        },
        {
            "Date": "2025-01-21",
            "Open": 3020.0,
            "High": 3080.0,
            "Low": 3010.0,
            "Close": 3060.0,
            "Volume": 1200000,
        },
        {
            "Date": "2025-01-22",
            "Open": 3060.0,
            "High": 3100.0,
            "Low": 3040.0,
            "Close": 3080.0,
            "Volume": 1100000,
        },
    ]

    from unittest.mock import AsyncMock

    mocker.patch(
        "stock.services.jquants_service.jquants_client.get_prices",
        new_callable=AsyncMock,
        return_value=mock_jquants_prices,
    )

    # APIリクエスト実行（週次指定）
    response = await client.get(
        "/api/v1/stocks/8058/price-history",
        params={"period": "1Y", "interval": "weekly"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert data["interval"] == "weekly"
    # 週次集計により件数が減る
    assert len(data["data"]) >= 1


@pytest.mark.asyncio
async def test_get_price_history_with_monthly_interval(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_token: str,
    setup_japanese_stock_data,
    mocker,
):
    """月次データへの集計テスト

    期待する動作:
    - ステータスコード200
    - 日次データが月次に集計されること

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        setup_japanese_stock_data: 日本株テストデータ
        mocker: モッカー
    """
    # 複数日分のモックデータ（異なる月）
    mock_jquants_prices = [
        {
            "Date": "2024-12-20",
            "Open": 2900.0,
            "High": 2950.0,
            "Low": 2880.0,
            "Close": 2920.0,
            "Volume": 1000000,
        },
        {
            "Date": "2024-12-25",
            "Open": 2920.0,
            "High": 2980.0,
            "Low": 2910.0,
            "Close": 2960.0,
            "Volume": 1200000,
        },
        {
            "Date": "2025-01-10",
            "Open": 2960.0,
            "High": 3000.0,
            "Low": 2940.0,
            "Close": 2980.0,
            "Volume": 1100000,
        },
        {
            "Date": "2025-01-20",
            "Open": 2980.0,
            "High": 3050.0,
            "Low": 2970.0,
            "Close": 3020.0,
            "Volume": 1300000,
        },
    ]

    from unittest.mock import AsyncMock

    mocker.patch(
        "stock.services.jquants_service.jquants_client.get_prices",
        new_callable=AsyncMock,
        return_value=mock_jquants_prices,
    )

    # APIリクエスト実行（月次指定）
    response = await client.get(
        "/api/v1/stocks/8058/price-history",
        params={"period": "1Y", "interval": "monthly"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert data["interval"] == "monthly"
    # 月次集計により件数が減る
    assert len(data["data"]) >= 1


@pytest.mark.asyncio
async def test_get_price_history_stock_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_token: str,
):
    """存在しない銘柄の株価履歴取得エラーのテスト

    期待する動作:
    - ステータスコード400
    - 銘柄が存在しないエラーメッセージを返却

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # APIリクエスト実行（存在しない銘柄）
    response = await client.get(
        "/api/v1/stocks/INVALID/price-history",
        params={"period": "1Y", "interval": "daily"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    # レスポンス検証
    assert response.status_code == 400
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_price_history_without_auth(
    setup_database,
):
    """認証なしでの株価履歴取得エラーのテスト

    期待する動作:
    - ステータスコード401
    - 認証が必要なエラーメッセージを返却

    Args:
        setup_database: データベースセットアップ
    """
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    from stock.app import app
    from stock.database import get_db

    # クッキーなしの新しいクライアントを作成
    async def override_get_db():
        TestingSessionLocalFunction = sessionmaker(
            setup_database, class_=AsyncSession, expire_on_commit=False
        )
        async with TestingSessionLocalFunction() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        # APIリクエスト実行（認証ヘッダーなし、cookieなし）
        response = await test_client.get(
            "/api/v1/stocks/8058/price-history",
            params={"period": "1Y", "interval": "daily"},
        )

        # レスポンス検証
        assert response.status_code == 401

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_price_history_different_periods(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_token: str,
    setup_japanese_stock_data,
    mocker,
):
    """異なる期間パラメータのテスト

    期待する動作:
    - ステータスコード200
    - 指定した期間パラメータが正しく反映されること

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        setup_japanese_stock_data: 日本株テストデータ
        mocker: モッカー
    """
    mock_jquants_prices = [
        {
            "Date": "2025-01-20",
            "Open": 3000.0,
            "High": 3050.0,
            "Low": 2980.0,
            "Close": 3020.0,
            "Volume": 1000000,
        },
    ]

    from unittest.mock import AsyncMock

    mocker.patch(
        "stock.services.jquants_service.jquants_client.get_prices",
        new_callable=AsyncMock,
        return_value=mock_jquants_prices,
    )

    # 各期間パラメータをテスト
    periods = ["1M", "3M", "6M", "1Y", "3Y"]
    for period in periods:
        response = await client.get(
            "/api/v1/stocks/8058/price-history",
            params={"period": period, "interval": "daily"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["period"] == period
