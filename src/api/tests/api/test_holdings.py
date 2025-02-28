from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


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
