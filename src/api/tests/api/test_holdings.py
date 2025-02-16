from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from stock.schemas import StockCreate, TransactionCreate


@pytest.mark.asyncio
async def test_recalculate_holding_pl_japanese_stock(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """
    日本株の保有損益再計算テスト
    - 期待する動作:
        - ステータスコード200
        - 更新された保有情報を返却
    """
    # 事前に銘柄を登録
    stock_data = StockCreate(symbol="7203")
    await client.post("/api/v1/stocks/", json=stock_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"})

    # 購入取引を登録
    transaction_data = TransactionCreate(
        symbol="7203",
        transaction_type="buy",
        quantity=Decimal("10.0"),
        price=Decimal("1000.0"),
        account_type="NISA(成長投資枠)",
        fee=Decimal("0.0"),
        tax=Decimal("0.0"),
        transaction_date="2024-01-01T00:00:00",
    )
    await client.post(
        "/api/v1/transactions/", json=transaction_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )

    # 保有損益再計算APIを呼び出し
    response = await client.post("/api/v1/holdings/7203/recalculate", headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "7203"
    assert Decimal(data["quantity"]) == Decimal("10.0")
    assert data["market_value"] is not None
    assert data["unrealized_pl"] is not None
    assert data["unrealized_pl_percentage"] is not None


@pytest.mark.asyncio
async def test_recalculate_holding_pl_us_stock(client: AsyncClient, db_session: AsyncSession, auth_token: str, mocker):
    """
    米国株の保有損益再計算テスト
    - 期待する動作:
        - ステータスコード200
        - 更新された保有情報を返却
        - AlphaVantage APIのモックが呼び出されること
    """
    # AlphaVantage APIのモック
    mock_fetch_usdjpy_rate = mocker.patch("stock.services.alphavantage_service.fetch_usdjpy_rate", return_value=150.0)

    # 事前に銘柄を登録
    stock_data = StockCreate(symbol="AAPL")
    await client.post("/api/v1/stocks/", json=stock_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"})

    # 購入取引を登録
    transaction_data = TransactionCreate(
        symbol="AAPL",
        transaction_type="buy",
        quantity=Decimal("10.0"),
        price=Decimal("150.0"),  # USD価格
        account_type="NISA(成長投資枠)",
        fee=Decimal("0.0"),
        tax=Decimal("0.0"),
        transaction_date="2024-01-01T00:00:00",
    )
    await client.post(
        "/api/v1/transactions/", json=transaction_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )

    # 保有損益再計算APIを呼び出し
    response = await client.post("/api/v1/holdings/AAPL/recalculate", headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert Decimal(data["quantity"]) == Decimal("10.0")
    assert data["market_value"] is not None
    assert data["unrealized_pl"] is not None
    assert data["unrealized_pl_percentage"] is not None

    # モックが呼び出されたことを確認
    mock_fetch_usdjpy_rate.assert_called_once()


@pytest.mark.asyncio
async def test_list_holdings(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """
    保有銘柄一覧取得を確認するテスト
    - 期待する動作:
        - ステータスコード200
        - 保有銘柄情報に銘柄名が含まれている
    """
    # 事前に銘柄を登録
    stock_data = StockCreate(symbol="8058", name="Toyota Motor Corporation")
    await client.post("/api/v1/stocks/", json=stock_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"})

    # 事前に購入取引を登録
    transaction_data = TransactionCreate(
        symbol="8058",
        transaction_type="buy",
        quantity=Decimal("10.0"),
        price=Decimal("3000.0"),
        account_type="NISA(成長投資枠)",
        fee=Decimal("0.0"),
        tax=Decimal("0.0"),
        transaction_date="2024-01-01T00:00:00",
    )
    await client.post(
        "/api/v1/transactions/", json=transaction_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )

    # 保有銘柄一覧を取得
    response = await client.get("/api/v1/holdings/", headers={"Authorization": f"Bearer {auth_token}"})

    # レスポンスの検証
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["stock_name"] == "三菱商事"
