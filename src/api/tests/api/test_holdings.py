from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from ..conftest import (
    MOCK_JAPAN_STOCK_PRICE_UPDATED,
    MOCK_US_STOCK_PRICE_UPDATED,
    MOCK_USD_JPY_RATE_RESPONSE,
)


@pytest.mark.asyncio
async def test_recalculate_holding_pl_japanese_stock(
    client: AsyncClient, db_session: AsyncSession, auth_token: str, setup_japanese_stock_data
):
    """日本株の保有損益再計算テスト

    期待する動作:
    - ステータスコード200
    - 更新された保有情報を返却

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        setup_japanese_stock_data: 日本株のテストデータ
    """
    # 保有損益再計算APIを呼び出し
    response = await client.post("/api/v1/holdings/8058/recalculate", headers={"Authorization": f"Bearer {auth_token}"})

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "8058"
    assert Decimal(data["quantity"]) == Decimal("100.0")
    assert data["market_value"] is not None
    assert data["unrealized_pl"] is not None
    assert data["unrealized_pl_percentage"] is not None


@pytest.mark.asyncio
async def test_recalculate_holding_pl_us_stock(
    client: AsyncClient, db_session: AsyncSession, auth_token: str, setup_us_stock_data, mock_external_apis
):
    """米国株の保有損益再計算テスト

    期待する動作:
    - ステータスコード200
    - 更新された保有情報を返却
    - AlphaVantage APIのモックが呼び出されること

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        setup_us_stock_data: 米国株のテストデータ
        mock_external_apis: モック化されたAPI
    """
    # 保有損益再計算APIを呼び出し
    response = await client.post("/api/v1/holdings/AAPL/recalculate", headers={"Authorization": f"Bearer {auth_token}"})

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert Decimal(data["quantity"]) == Decimal("10.0")
    assert data["market_value"] is not None
    assert data["unrealized_pl"] is not None
    assert data["unrealized_pl_percentage"] is not None

    # トランザクション登録時の1回のAPI呼び出しを確認
    mock_external_apis["overview"].assert_called_once_with("AAPL")


@pytest.mark.asyncio
async def test_list_holdings(client: AsyncClient, db_session: AsyncSession, auth_token: str, setup_japanese_stock_data):
    """保有銘柄一覧取得を確認するテスト

    期待する動作:
    - ステータスコード200
    - 保有銘柄情報に銘柄名が含まれている

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        setup_japanese_stock_data: 日本株のテストデータ
    """
    # 保有銘柄一覧を取得
    response = await client.get("/api/v1/holdings/", headers={"Authorization": f"Bearer {auth_token}"})

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["stock_name"] == "三菱商事"


@pytest.mark.asyncio
async def test_recalculate_all_holdings_pl(
    client: AsyncClient, db_session: AsyncSession, auth_token: str, setup_japanese_stock_data, setup_us_stock_data
):
    """全銘柄の保有損益一括再計算のテスト

    期待する動作:
    - ステータスコード200
    - 日本株・米国株それぞれの更新された保有情報を返却
    - 各銘柄の最新株価が、初期価格から更新後価格に変更されていることを確認

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        setup_japanese_stock_data: 日本株のテストデータ
        setup_us_stock_data: 米国株のテストデータ
    """
    # 全銘柄の損益再計算APIを呼び出し
    response = await client.post("/api/v1/holdings/recalculate-all", headers={"Authorization": f"Bearer {auth_token}"})

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2  # 2銘柄分のデータがあることを確認

    # 各銘柄の更新を確認
    holdings = {h["symbol"]: h for h in data}

    # 日本株（8058）の検証
    assert "8058" in holdings
    jp_holding = holdings["8058"]
    assert Decimal(jp_holding["current_price"]) == MOCK_JAPAN_STOCK_PRICE_UPDATED  # 更新後の価格であることを確認
    assert Decimal(jp_holding["market_value"]) == MOCK_JAPAN_STOCK_PRICE_UPDATED * Decimal("100.0")
    assert jp_holding["unrealized_pl"] is not None
    assert jp_holding["unrealized_pl_percentage"] is not None

    # 米国株（AAPL）の検証
    assert "AAPL" in holdings
    us_holding = holdings["AAPL"]
    assert (
        Decimal(us_holding["current_price"]) == MOCK_US_STOCK_PRICE_UPDATED * MOCK_USD_JPY_RATE_RESPONSE
    )  # 更新後の価格であることを確認
    assert Decimal(us_holding["market_value"]) == MOCK_US_STOCK_PRICE_UPDATED * MOCK_USD_JPY_RATE_RESPONSE * Decimal("10.0")
    assert us_holding["unrealized_pl"] is not None
    assert us_holding["unrealized_pl_percentage"] is not None
