from datetime import datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from stock.models import Stock
from stock.schemas import StockCreate, TransactionCreate


@pytest.fixture
async def test_stock(db_session: AsyncSession):
    """テスト用の株式データを作成するフィクスチャー"""
    stock = Stock(
        symbol="AAPL",
        name="Apple Inc.",
        name_en="Apple Inc.",
        market="NASDAQ",
        security_type="STOCK",
        currency="USD",
    )
    db_session.add(stock)
    await db_session.commit()
    await db_session.refresh(stock)
    return stock


@pytest.mark.asyncio
async def test_create_dividend(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """
    配当情報の登録テスト
    - 事前条件:
        - 銘柄の登録
        - 株式の購入取引
    - 期待する動作:
        - ステータスコード200
        - 登録された配当情報を返却
        - 保有情報の配当総額が更新される
    """
    # 事前に銘柄を登録
    stock_data = StockCreate(symbol="8058")
    await client.post(
        "/api/v1/stocks/", json=stock_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )

    # 事前に購入取引を登録
    transaction_data = TransactionCreate(
        symbol="8058",
        transaction_type="buy",
        quantity=Decimal("100.0"),
        price=Decimal("3000.0"),
        account_type="NISA(成長投資枠)",
        fee=Decimal("0.0"),
        tax=Decimal("0.0"),
        transaction_date="2024-01-01T00:00:00",
    )
    await client.post(
        "/api/v1/transactions/", json=transaction_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )

    # 配当情報の登録
    dividend_data = {
        "symbol": "8058",
        "payment_date": "2024-03-15T00:00:00Z",
        "shares_owned": "100.0",
        "total_amount": "25000.0",
        "tax": "2500.0",
        "fee": "0.0"
    }

    response = await client.post(
        "/api/v1/dividends/",
        json=dividend_data,
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    # レスポンスの検証
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == dividend_data["symbol"]
    assert datetime.fromisoformat(data["payment_date"]).strftime("%Y-%m-%dT%H:%M:%S") == "2024-03-15T00:00:00"
    assert Decimal(data["total_amount"]) == Decimal(dividend_data["total_amount"])
    assert Decimal(data["tax"]) == Decimal(dividend_data["tax"])
    assert Decimal(data["fee"]) == Decimal(dividend_data["fee"])

    # 保有情報の確認（配当金が反映されているか）
    holdings_response = await client.get("/api/v1/portfolio/holdings/", headers={"Authorization": f"Bearer {auth_token}"})
    assert holdings_response.status_code == 200
    holdings = holdings_response.json()
    holding = next((h for h in holdings if h["symbol"] == "8058"), None)
    assert holding is not None
    # 配当金の純額（25000 - 2500 = 22500）が反映されていることを確認
    assert Decimal(holding["total_dividend"]) == Decimal("22500.0")


@pytest.mark.asyncio
async def test_create_dividend_stock_not_found(client: AsyncClient, auth_token: str):
    """
    存在しない銘柄の配当情報登録テスト
    - 期待する動作:
        - ステータスコード404
        - エラーメッセージを返却
    """
    dividend_data = {
        "symbol": "INVALID",
        "payment_date": "2024-03-15T00:00:00Z",
        "shares_owned": "100.0",
        "total_amount": "25000.0",
        "tax": "2500.0",
        "fee": "0.0"
    }

    response = await client.post(
        "/api/v1/dividends/",
        json=dividend_data,
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Stock not found"


@pytest.mark.asyncio
async def test_list_dividends(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """
    配当一覧取得テスト
    - 事前条件:
        - 銘柄の登録
        - 株式の購入取引
        - 複数の配当情報の登録
    - 期待する動作:
        - ステータスコード200
        - 登録された配当情報が支払日の降順で返却される
    """
    # 事前に銘柄を登録
    stock_data = StockCreate(symbol="8058")
    await client.post(
        "/api/v1/stocks/", json=stock_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )

    # 事前に購入取引を登録
    transaction_data = TransactionCreate(
        symbol="8058",
        transaction_type="buy",
        quantity=Decimal("100.0"),
        price=Decimal("3000.0"),
        account_type="NISA(成長投資枠)",
        fee=Decimal("0.0"),
        tax=Decimal("0.0"),
        transaction_date="2024-01-01T00:00:00",
    )
    await client.post(
        "/api/v1/transactions/", json=transaction_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )

    # 複数の配当情報を登録
    dividend_data_list = [
        {
            "symbol": "8058",
            "payment_date": "2024-03-15T00:00:00Z",
            "shares_owned": "100.0",
            "total_amount": "25000.0",
            "tax": "2500.0",
            "fee": "0.0"
        },
        {
            "symbol": "8058",
            "payment_date": "2024-02-15T00:00:00Z",
            "shares_owned": "100.0",
            "total_amount": "25000.0",
            "tax": "2500.0",
            "fee": "0.0"
        }
    ]

    for dividend_data in dividend_data_list:
        await client.post(
            "/api/v1/dividends/",
            json=dividend_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

    # 配当一覧を取得
    response = await client.get("/api/v1/dividends/", headers={"Authorization": f"Bearer {auth_token}"})
    
    # レスポンスの検証
    assert response.status_code == 200
    data = response.json()
    
    # 2件の配当情報が取得できることを確認
    assert len(data) == 2
    
    # 支払日の降順でソートされていることを確認
    assert datetime.fromisoformat(data[0]["payment_date"]) > datetime.fromisoformat(data[1]["payment_date"])
    
    # 各配当情報の内容を確認
    for dividend in data:
        assert dividend["symbol"] == "8058"
        assert Decimal(dividend["total_amount"]) == Decimal("25000.0")
        assert Decimal(dividend["tax"]) == Decimal("2500.0")
        assert Decimal(dividend["fee"]) == Decimal("0.0")