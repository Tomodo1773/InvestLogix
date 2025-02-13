from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from stock.schemas import StockCreate, TransactionCreate


@pytest.mark.asyncio
async def test_create_buy_transaction(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """
    株式購入取引の登録テスト
    - 期待する動作:
        - ステータスコード200
        - 登録された取引情報を返却
    """
    # 事前に銘柄を登録
    stock_data = StockCreate(symbol="8058")
    stock_response = await client.post(
        "/api/v1/stocks/", json=stock_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert stock_response.status_code == 200

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
    response = await client.post(
        "/api/v1/transactions/", json=transaction_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "8058"
    assert data["transaction_type"] == "buy"
    assert Decimal(data["quantity"]) == Decimal("10.0")
    assert Decimal(data["price"]) == Decimal("3000.0")


@pytest.mark.asyncio
async def test_create_sell_transaction(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """
    株式売却取引の登録テスト
    - 期待する動作:
        - ステータスコード200
        - 登録された取引情報を返却
    """
    # 事前に銘柄を登録
    stock_data = StockCreate(symbol="8058")
    stock_response = await client.post(
        "/api/v1/stocks/", json=stock_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert stock_response.status_code == 200

    # 事前に購入取引を登録
    buy_transaction = TransactionCreate(
        symbol="8058",
        transaction_type="buy",
        quantity=Decimal("10.0"),
        price=Decimal("3000.0"),
        account_type="NISA(成長投資枠)",
        fee=Decimal("0.0"),
        tax=Decimal("0.0"),
        transaction_date="2024-01-01T00:00:00",
    )
    buy_response = await client.post(
        "/api/v1/transactions/", json=buy_transaction.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert buy_response.status_code == 200

    # 売却取引のテスト
    transaction_data = TransactionCreate(
        symbol="8058",
        transaction_type="sell",
        quantity=Decimal("5.0"),
        price=Decimal("3500.0"),
        account_type="NISA(成長投資枠)",
        fee=Decimal("0.0"),
        tax=Decimal("0.0"),
        transaction_date="2024-01-01T00:00:00",
    )
    response = await client.post(
        "/api/v1/transactions/", json=transaction_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "8058"
    assert data["transaction_type"] == "sell"
    assert Decimal(data["quantity"]) == Decimal("5.0")
    assert Decimal(data["price"]) == Decimal("3500.0")


@pytest.mark.asyncio
async def test_create_transaction_insufficient_shares(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """
    保有株数不足による売却取引の失敗テスト
    - 期待する動作:
        - ステータスコード400
        - エラーメッセージを返却
    """
    # 事前に銘柄を登録
    stock_data = StockCreate(symbol="8058")
    stock_response = await client.post(
        "/api/v1/stocks/", json=stock_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert stock_response.status_code == 200

    # 売却取引のテスト（保有数量ゼロで売却）
    transaction_data = TransactionCreate(
        symbol="8058",
        transaction_type="sell",
        quantity=Decimal("100.0"),
        price=Decimal("3500.0"),
        account_type="NISA(成長投資枠)",
        fee=Decimal("0.0"),
        tax=Decimal("0.0"),
        transaction_date="2024-01-01T00:00:00",
    )
    response = await client.post(
        "/api/v1/transactions/", json=transaction_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Insufficient shares"


@pytest.mark.asyncio
async def test_create_transaction_stock_not_found(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """
    存在しない銘柄による取引の失敗テスト
    - 期待する動作:
        - ステータスコード404
        - エラーメッセージを返却
    """
    transaction_data = TransactionCreate(
        symbol="INVALID",
        transaction_type="buy",
        quantity=Decimal("10.0"),
        price=Decimal("3000.0"),
        account_type="NISA(成長投資枠)",
        fee=Decimal("0.0"),
        tax=Decimal("0.0"),
        transaction_date="2024-01-01T00:00:00",
    )
    response = await client.post(
        "/api/v1/transactions/", json=transaction_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Stock not found"


@pytest.mark.asyncio
async def test_multiple_buy_transactions_average_cost(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """
    複数回の購入取引による平均取得単価の計算テスト
    - 期待する動作:
        - 1回目の購入: 10株@3000円
        - 2回目の購入: 5株@4000円
        - 保有数量: 15株
        - 平均取得単価: ((10 * 3000) + (5 * 4000)) / 15 = 3333.33...円
    """
    # 事前に銘柄を登録
    stock_data = StockCreate(symbol="8058")
    await client.post("/api/v1/stocks/", json=stock_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"})

    # 1回目の購入取引（10株@3000円）
    first_buy = TransactionCreate(
        symbol="8058",
        transaction_type="buy",
        quantity=Decimal("10.0"),
        price=Decimal("3000.0"),
        account_type="NISA(成長投資枠)",
        fee=Decimal("0.0"),
        tax=Decimal("0.0"),
        transaction_date="2024-01-01T00:00:00",
    )
    await client.post("/api/v1/transactions/", json=first_buy.model_dump(), headers={"Authorization": f"Bearer {auth_token}"})

    # 2回目の購入取引（5株@4000円）
    second_buy = TransactionCreate(
        symbol="8058",
        transaction_type="buy",
        quantity=Decimal("5.0"),
        price=Decimal("4000.0"),
        account_type="NISA(成長投資枠)",
        fee=Decimal("0.0"),
        tax=Decimal("0.0"),
        transaction_date="2024-01-02T00:00:00",
    )
    await client.post("/api/v1/transactions/", json=second_buy.model_dump(), headers={"Authorization": f"Bearer {auth_token}"})

    # ポートフォリオから保有情報を取得して確認
    holdings_response = await client.get("/api/v1/portfolio/holdings/", headers={"Authorization": f"Bearer {auth_token}"})
    assert holdings_response.status_code == 200
    holdings = holdings_response.json()

    # 指定した銘柄の保有情報を検索
    holding = next((h for h in holdings if h["symbol"] == "8058"), None)
    assert holding is not None
    assert Decimal(holding["quantity"]) == Decimal("15.0")
    assert Decimal(holding["average_cost"]) == Decimal("3333.33").quantize(Decimal("0.01"))
    assert Decimal(holding["total_cost"]) == Decimal("50000.00").quantize(Decimal("0.01"))


@pytest.mark.asyncio
async def test_buy_and_partial_sell_calculation(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """
    購入後の一部売却時の売却益と保有株数の計算テスト
    - 期待する動作:
        - 1回目の購入: 100株@1000円 = 100,000円
        - 一部売却: 60株@1500円
            - 売却益: (1500円 - 1000円) * 60株 = 30,000円
            - 残り保有数: 40株
            - 平均取得単価: 1000円（変化なし）
            - 残りの取得価額合計: 1000円 * 40株 = 40,000円
    """
    # 事前に銘柄を登録
    stock_data = StockCreate(symbol="7203")
    await client.post("/api/v1/stocks/", json=stock_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"})

    # 購入取引（100株@1000円）
    buy_transaction = TransactionCreate(
        symbol="7203",
        transaction_type="buy",
        quantity=Decimal("100.0"),
        price=Decimal("1000.0"),
        account_type="NISA(成長投資枠)",
        fee=Decimal("0.0"),
        tax=Decimal("0.0"),
        transaction_date="2024-01-01T00:00:00",
    )
    await client.post(
        "/api/v1/transactions/", json=buy_transaction.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )

    # 一部売却取引（60株@1500円）
    sell_transaction = TransactionCreate(
        symbol="7203",
        transaction_type="sell",
        quantity=Decimal("60.0"),
        price=Decimal("1500.0"),
        account_type="NISA(成長投資枠)",
        fee=Decimal("0.0"),
        tax=Decimal("0.0"),
        transaction_date="2024-01-02T00:00:00",
    )
    await client.post(
        "/api/v1/transactions/", json=sell_transaction.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )

    # ポートフォリオから保有情報を取得して確認
    holdings_response = await client.get("/api/v1/portfolio/holdings/", headers={"Authorization": f"Bearer {auth_token}"})
    assert holdings_response.status_code == 200
    holdings = holdings_response.json()

    # 指定した銘柄の保有情報を検索
    holding = next((h for h in holdings if h["symbol"] == "7203"), None)
    assert holding is not None

    # 保有数量の確認（100株 - 60株 = 40株）
    assert Decimal(holding["quantity"]) == Decimal("40.0")

    # 平均取得単価の確認（1000円のまま変化なし）
    assert Decimal(holding["average_cost"]) == Decimal("1000.0")

    # 取得価額合計の確認（1000円 * 40株 = 40,000円）
    assert Decimal(holding["total_cost"]) == Decimal("40000.0")

    # 売却益の確認（(1500円 - 1000円) * 60株 = 30,000円）
    assert Decimal(holding["realized_pl"]) == Decimal("30000.0")
