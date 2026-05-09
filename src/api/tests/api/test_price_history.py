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
    # J-Quants APIのモックを設定（V2形式、調整済み株価フィールドを使用）
    mock_jquants_prices = [
        {
            "Date": "2025-01-20",
            "AdjO": 3000.0,
            "AdjH": 3050.0,
            "AdjL": 2980.0,
            "AdjC": 3020.0,
            "AdjVo": 1000000,
        },
        {
            "Date": "2025-01-21",
            "AdjO": 3020.0,
            "AdjH": 3080.0,
            "AdjL": 3010.0,
            "AdjC": 3060.0,
            "AdjVo": 1200000,
        },
    ]

    # 非同期関数なので、AsyncMockを使用
    from unittest.mock import AsyncMock

    # get_jquants_client()が返すモックオブジェクトを作成
    mock_client = mocker.MagicMock()
    mock_client.get_prices = AsyncMock(return_value=mock_jquants_prices)

    # price_history_serviceでインポートされたget_jquants_clientをモック化
    mock_get_prices = mocker.patch(
        "stock.services.price_history_service.get_jquants_client",
        return_value=mock_client,
    )

    # APIリクエスト実行
    response = await client.get(
        "/api/v1/symbols/8058/price-history",
        params={"interval": "daily", "limit": 80},
    )

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "8058"
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
        "/api/v1/symbols/AAPL/price-history",
        params={"interval": "daily", "limit": 80},
    )

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
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
    # 複数日分のモックデータ（同じ週の月曜〜金曜、V2形式）
    mock_jquants_prices = [
        {
            "Date": "2025-01-20",
            "AdjO": 3000.0,
            "AdjH": 3050.0,
            "AdjL": 2980.0,
            "AdjC": 3020.0,
            "AdjVo": 1000000,
        },
        {
            "Date": "2025-01-21",
            "AdjO": 3020.0,
            "AdjH": 3080.0,
            "AdjL": 3010.0,
            "AdjC": 3060.0,
            "AdjVo": 1200000,
        },
        {
            "Date": "2025-01-22",
            "AdjO": 3060.0,
            "AdjH": 3100.0,
            "AdjL": 3040.0,
            "AdjC": 3080.0,
            "AdjVo": 1100000,
        },
    ]

    from unittest.mock import AsyncMock

    mock_client = mocker.MagicMock()
    mock_client.get_prices = AsyncMock(return_value=mock_jquants_prices)

    mocker.patch(
        "stock.services.price_history_service.get_jquants_client",
        return_value=mock_client,
    )

    # APIリクエスト実行（週次指定）
    response = await client.get(
        "/api/v1/symbols/8058/price-history",
        params={"interval": "weekly", "limit": 80},
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
    # 複数日分のモックデータ（異なる月、V2形式）
    mock_jquants_prices = [
        {
            "Date": "2024-12-20",
            "AdjO": 2900.0,
            "AdjH": 2950.0,
            "AdjL": 2880.0,
            "AdjC": 2920.0,
            "AdjVo": 1000000,
        },
        {
            "Date": "2024-12-25",
            "AdjO": 2920.0,
            "AdjH": 2980.0,
            "AdjL": 2910.0,
            "AdjC": 2960.0,
            "AdjVo": 1200000,
        },
        {
            "Date": "2025-01-10",
            "AdjO": 2960.0,
            "AdjH": 3000.0,
            "AdjL": 2940.0,
            "AdjC": 2980.0,
            "AdjVo": 1100000,
        },
        {
            "Date": "2025-01-20",
            "AdjO": 2980.0,
            "AdjH": 3050.0,
            "AdjL": 2970.0,
            "AdjC": 3020.0,
            "AdjVo": 1300000,
        },
    ]

    from unittest.mock import AsyncMock

    mock_client = mocker.MagicMock()
    mock_client.get_prices = AsyncMock(return_value=mock_jquants_prices)

    mocker.patch(
        "stock.services.price_history_service.get_jquants_client",
        return_value=mock_client,
    )

    # APIリクエスト実行（月次指定）
    response = await client.get(
        "/api/v1/symbols/8058/price-history",
        params={"interval": "monthly", "limit": 60},
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
        "/api/v1/symbols/INVALID/price-history",
        params={"interval": "daily", "limit": 80},
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
            "/api/v1/symbols/8058/price-history",
            params={"interval": "daily", "limit": 80},
        )

        # レスポンス検証
        assert response.status_code == 401

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_price_history_with_limit(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_token: str,
    setup_japanese_stock_data,
    mocker,
):
    """limitパラメータのテスト

    期待する動作:
    - ステータスコード200
    - 指定したlimitパラメータ以下のデータ件数が返されること

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        setup_japanese_stock_data: 日本株テストデータ
        mocker: モッカー
    """
    # 多数のデータを生成
    from datetime import datetime, timedelta

    base_date = datetime(2025, 1, 1)
    mock_jquants_prices = [
        {
            "Date": (base_date + timedelta(days=i - 1)).strftime("%Y-%m-%d"),
            "AdjO": 3000.0,
            "AdjH": 3050.0,
            "AdjL": 2980.0,
            "AdjC": 3020.0,
            "AdjVo": 1000000,
        }
        for i in range(1, 101)
    ]

    from unittest.mock import AsyncMock

    mock_client = mocker.MagicMock()
    mock_client.get_prices = AsyncMock(return_value=mock_jquants_prices)

    mocker.patch(
        "stock.services.price_history_service.get_jquants_client",
        return_value=mock_client,
    )

    # limit=10でテスト
    response = await client.get(
        "/api/v1/symbols/8058/price-history",
        params={"interval": "daily", "limit": 10},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 10


@pytest.mark.asyncio
async def test_get_index_price_history(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_token: str,
    mocker,
):
    """主要株価指数の取得テスト（正常系）

    期待する動作:
    - DB登録不要でステータスコード200
    - Stooqから指数シンボル（^spx）で取得されること
    """
    mock_index_data = [
        {
            "date": "2025-01-20",
            "open": 5800.0,
            "high": 5850.0,
            "low": 5780.0,
            "close": 5820.0,
            "volume": 0,
        },
        {
            "date": "2025-01-21",
            "open": 5820.0,
            "high": 5880.0,
            "low": 5810.0,
            "close": 5860.0,
            "volume": 0,
        },
    ]

    mock_fetch_index = mocker.patch(
        "stock.services.price_history_service.PriceHistoryService._fetch_index_prices_cached",
        return_value=mock_index_data,
    )

    response = await client.get(
        "/api/v1/symbols/SP500/price-history",
        params={"interval": "daily", "limit": 10},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "SP500"
    assert data["interval"] == "daily"
    assert len(data["data"]) == 2
    assert data["data"][0]["close"] == 5820.0

    mock_fetch_index.assert_called_once()
    assert mock_fetch_index.call_args.args[0] == "^spx"


@pytest.mark.asyncio
async def test_get_price_history_monthly_limit_validation(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_token: str,
    setup_japanese_stock_data,
):
    """月足のlimit上限検証テスト

    期待する動作:
    - limit > 60の場合、ステータスコード400
    - エラーメッセージが返されること

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        setup_japanese_stock_data: 日本株テストデータ
    """
    # limit=61でリクエスト（月足の上限60を超える）
    response = await client.get(
        "/api/v1/symbols/8058/price-history",
        params={"interval": "monthly", "limit": 61},
    )

    assert response.status_code == 400
    data = response.json()
    assert "60" in data["detail"]
