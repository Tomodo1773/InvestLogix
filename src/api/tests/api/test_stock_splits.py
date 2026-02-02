from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_stock_split_and_recalculate(
    client: AsyncClient, db_session: AsyncSession, auth_token: str
):
    """株式分割登録と過去取引の調整値再計算のテスト

    期待する動作:
    - 株式分割を登録すると、過去取引の調整値が自動的に再計算される
    - 分割比率4:1の場合、数量は4倍、価格は1/4になる

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # 1. 分割前の取引を登録（100株@10000円）
    transaction_data = {
        "symbol": "8058",
        "transaction_type": "buy",
        "quantity": "100.0",
        "price": "10000.0",
        "account_type": "特定",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }
    response = await client.post(
        "/api/v1/transactions/", json=transaction_data, headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200

    # 2. 4:1の株式分割を登録
    split_data = {
        "symbol": "8058",
        "split_date": "2024-06-01T00:00:00",
        "split_ratio": "4.0",
    }
    split_response = await client.post(
        "/api/v1/stock-splits/", json=split_data, headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert split_response.status_code == 201
    split_result = split_response.json()
    assert split_result["symbol"] == "8058"
    assert Decimal(split_result["split_ratio"]) == Decimal("4.0")

    # 3. 取引の調整値を確認（400株@2500円）
    transactions_response = await client.get(
        "/api/v1/transactions/?symbol=8058", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert transactions_response.status_code == 200
    transactions = transactions_response.json()
    transaction = transactions[0]
    assert Decimal(transaction["quantity"]) == Decimal("100.0")  # 元の数量は変わらない
    assert Decimal(transaction["price"]) == Decimal("10000.0")  # 元の価格は変わらない
    assert Decimal(transaction["adjusted_quantity"]) == Decimal("400.0")  # 調整後: 100 * 4
    assert Decimal(transaction["adjusted_price"]) == Decimal("2500.0")  # 調整後: 10000 / 4


@pytest.mark.asyncio
async def test_holding_calculation_with_split(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """分割後の保有株計算が正しいことを確認

    期待する動作:
    - 分割前に100株@10000円で購入
    - 4:1分割を登録
    - 保有株情報が調整済み値で計算される（400株@2500円）

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # 1. 分割前の取引を登録（100株@10000円）
    transaction_data = {
        "symbol": "8058",
        "transaction_type": "buy",
        "quantity": "100.0",
        "price": "10000.0",
        "account_type": "特定",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }
    await client.post(
        "/api/v1/transactions/", json=transaction_data, headers={"Authorization": f"Bearer {auth_token}"}
    )

    # 2. 4:1の株式分割を登録
    split_data = {
        "symbol": "8058",
        "split_date": "2024-06-01T00:00:00",
        "split_ratio": "4.0",
    }
    await client.post(
        "/api/v1/stock-splits/", json=split_data, headers={"Authorization": f"Bearer {auth_token}"}
    )

    # 3. 保有株情報を取得して再計算
    recalc_response = await client.post(
        "/api/v1/holdings/8058/recalculate", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert recalc_response.status_code == 200

    # 4. 保有株情報を確認
    holdings_response = await client.get(
        "/api/v1/holdings/?symbol=8058", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert holdings_response.status_code == 200
    holdings = holdings_response.json()
    holding = holdings[0]

    # 数量=400株、平均取得単価=2500円であることを確認
    assert Decimal(holding["quantity"]) == Decimal("400.0")
    assert Decimal(holding["average_cost"]) == Decimal("2500.0")
    assert Decimal(holding["total_cost"]) == Decimal("1000000.0")  # 400 * 2500


@pytest.mark.asyncio
async def test_sell_after_split_realized_pl(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """分割後の売却時に正しい実現損益が計算されることを確認

    期待する動作:
    - 分割前に100株@10000円で購入
    - 4:1分割を登録
    - 分割後に200株@3000円で売却
    - 実現損益 = (3000 - 2500) * 200 = 100000円

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # 1. 分割前の取引を登録（100株@10000円）
    buy_data = {
        "symbol": "8058",
        "transaction_type": "buy",
        "quantity": "100.0",
        "price": "10000.0",
        "account_type": "特定",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }
    await client.post(
        "/api/v1/transactions/", json=buy_data, headers={"Authorization": f"Bearer {auth_token}"}
    )

    # 2. 4:1の株式分割を登録
    split_data = {
        "symbol": "8058",
        "split_date": "2024-06-01T00:00:00",
        "split_ratio": "4.0",
    }
    await client.post(
        "/api/v1/stock-splits/", json=split_data, headers={"Authorization": f"Bearer {auth_token}"}
    )

    # 3. 分割後に200株@3000円で売却
    sell_data = {
        "symbol": "8058",
        "transaction_type": "sell",
        "quantity": "200.0",
        "price": "3000.0",
        "account_type": "特定",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-07-01T00:00:00",
    }
    sell_response = await client.post(
        "/api/v1/transactions/", json=sell_data, headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert sell_response.status_code == 200
    sell_transaction = sell_response.json()

    # 4. 実現損益を確認: (3000 - 2500) * 200 = 100000円
    assert Decimal(sell_transaction["realized_pl"]) == Decimal("100000.0")

    # 5. 保有株情報を確認（残り200株）
    holdings_response = await client.get(
        "/api/v1/holdings/?symbol=8058", headers={"Authorization": f"Bearer {auth_token}"}
    )
    holdings = holdings_response.json()
    holding = holdings[0]
    assert Decimal(holding["quantity"]) == Decimal("200.0")  # 400 - 200
    assert Decimal(holding["realized_pl"]) == Decimal("100000.0")


@pytest.mark.asyncio
async def test_recalculate_idempotency(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """調整値計算の冪等性を確認

    期待する動作:
    - 同じ計算を複数回実行しても結果が同じ

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # 1. 分割前の取引を登録
    transaction_data = {
        "symbol": "8058",
        "transaction_type": "buy",
        "quantity": "100.0",
        "price": "10000.0",
        "account_type": "特定",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }
    await client.post(
        "/api/v1/transactions/", json=transaction_data, headers={"Authorization": f"Bearer {auth_token}"}
    )

    # 2. 株式分割を登録
    split_data = {
        "symbol": "8058",
        "split_date": "2024-06-01T00:00:00",
        "split_ratio": "4.0",
    }
    await client.post(
        "/api/v1/stock-splits/", json=split_data, headers={"Authorization": f"Bearer {auth_token}"}
    )

    # 3. 1回目の取引情報取得
    response1 = await client.get(
        "/api/v1/transactions/?symbol=8058", headers={"Authorization": f"Bearer {auth_token}"}
    )
    transaction1 = response1.json()[0]

    # 4. 再計算を実行
    await client.post(
        "/api/v1/stock-splits/8058/recalculate", headers={"Authorization": f"Bearer {auth_token}"}
    )

    # 5. 2回目の取引情報取得
    response2 = await client.get(
        "/api/v1/transactions/?symbol=8058", headers={"Authorization": f"Bearer {auth_token}"}
    )
    transaction2 = response2.json()[0]

    # 6. 1回目と2回目で調整値が同じであることを確認
    assert Decimal(transaction1["adjusted_quantity"]) == Decimal(transaction2["adjusted_quantity"])
    assert Decimal(transaction1["adjusted_price"]) == Decimal(transaction2["adjusted_price"])


@pytest.mark.asyncio
async def test_list_stock_splits_all(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """全銘柄の株式分割履歴取得のテスト

    期待する動作:
    - 複数の銘柄の分割情報を登録
    - 全銘柄の分割履歴を取得できる

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # 0. 銘柄の取引を登録（銘柄を作成するため）
    for symbol in ["8058", "7203"]:
        transaction_data = {
            "symbol": symbol,
            "transaction_type": "buy",
            "quantity": "10.0",
            "price": "1000.0",
            "account_type": "特定",
            "fee": "0.0",
            "tax": "0.0",
            "transaction_date": "2024-01-01T00:00:00",
        }
        await client.post(
            "/api/v1/transactions/", json=transaction_data, headers={"Authorization": f"Bearer {auth_token}"}
        )

    # 1. 複数銘柄の分割情報を登録
    splits = [
        {"symbol": "8058", "split_date": "2024-06-01T00:00:00", "split_ratio": "4.0"},
        {"symbol": "7203", "split_date": "2024-07-01T00:00:00", "split_ratio": "5.0"},
    ]

    for split in splits:
        await client.post(
            "/api/v1/stock-splits/", json=split, headers={"Authorization": f"Bearer {auth_token}"}
        )

    # 2. 全銘柄の分割履歴を取得
    response = await client.get("/api/v1/stock-splits/", headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200
    result = response.json()

    # 3. 2件の分割情報が取得でき、銘柄名が含まれることを確認
    assert len(result) == 2
    for split in result:
        assert split["stock_name"] is not None


@pytest.mark.asyncio
async def test_list_stock_splits_by_symbol(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """特定銘柄の株式分割履歴取得のテスト

    期待する動作:
    - 複数の銘柄の分割情報を登録
    - 特定銘柄の分割履歴のみを取得できる

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # 0. 銘柄の取引を登録（銘柄を作成するため）
    for symbol in ["8058", "7203"]:
        transaction_data = {
            "symbol": symbol,
            "transaction_type": "buy",
            "quantity": "10.0",
            "price": "1000.0",
            "account_type": "特定",
            "fee": "0.0",
            "tax": "0.0",
            "transaction_date": "2024-01-01T00:00:00",
        }
        await client.post(
            "/api/v1/transactions/", json=transaction_data, headers={"Authorization": f"Bearer {auth_token}"}
        )

    # 1. 複数銘柄の分割情報を登録
    splits = [
        {"symbol": "8058", "split_date": "2024-06-01T00:00:00", "split_ratio": "4.0"},
        {"symbol": "7203", "split_date": "2024-07-01T00:00:00", "split_ratio": "5.0"},
    ]

    for split in splits:
        await client.post(
            "/api/v1/stock-splits/", json=split, headers={"Authorization": f"Bearer {auth_token}"}
        )

    # 2. 8058の分割履歴のみを取得
    response = await client.get(
        "/api/v1/stock-splits/?symbol=8058", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    result = response.json()

    # 3. 1件のみ取得され、8058の情報と銘柄名が含まれることを確認
    assert len(result) == 1
    assert result[0]["symbol"] == "8058"
    assert Decimal(result[0]["split_ratio"]) == Decimal("4.0")
    assert result[0]["stock_name"] is not None


@pytest.mark.asyncio
async def test_delete_stock_split(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """株式分割削除のテスト

    期待する動作:
    - 分割情報を削除すると、調整値が再計算される（NULLに戻る）

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # 1. 分割前の取引を登録
    transaction_data = {
        "symbol": "8058",
        "transaction_type": "buy",
        "quantity": "100.0",
        "price": "10000.0",
        "account_type": "特定",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }
    await client.post(
        "/api/v1/transactions/", json=transaction_data, headers={"Authorization": f"Bearer {auth_token}"}
    )

    # 2. 株式分割を登録
    split_data = {
        "symbol": "8058",
        "split_date": "2024-06-01T00:00:00",
        "split_ratio": "4.0",
    }
    split_response = await client.post(
        "/api/v1/stock-splits/", json=split_data, headers={"Authorization": f"Bearer {auth_token}"}
    )
    split_id = split_response.json()["split_id"]

    # 3. 調整値が設定されていることを確認
    response_before = await client.get(
        "/api/v1/transactions/?symbol=8058", headers={"Authorization": f"Bearer {auth_token}"}
    )
    transaction_before = response_before.json()[0]
    assert transaction_before["adjusted_quantity"] is not None
    assert transaction_before["adjusted_price"] is not None

    # 4. 分割情報を削除
    delete_response = await client.delete(
        f"/api/v1/stock-splits/{split_id}", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert delete_response.status_code == 204

    # 5. 調整値がNULLに戻っていることを確認
    response_after = await client.get(
        "/api/v1/transactions/?symbol=8058", headers={"Authorization": f"Bearer {auth_token}"}
    )
    transaction_after = response_after.json()[0]
    assert transaction_after["adjusted_quantity"] is None
    assert transaction_after["adjusted_price"] is None


@pytest.mark.asyncio
async def test_multiple_splits(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """複数回の株式分割のテスト

    期待する動作:
    - 2回の分割（4:1と2:1）が正しく適用される
    - 最終的な調整値は両方の分割比率の積（8倍）になる

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # 1. 分割前の取引を登録（100株@10000円）
    transaction_data = {
        "symbol": "8058",
        "transaction_type": "buy",
        "quantity": "100.0",
        "price": "10000.0",
        "account_type": "特定",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }
    await client.post(
        "/api/v1/transactions/", json=transaction_data, headers={"Authorization": f"Bearer {auth_token}"}
    )

    # 2. 1回目の分割（4:1）
    split1_data = {
        "symbol": "8058",
        "split_date": "2024-06-01T00:00:00",
        "split_ratio": "4.0",
    }
    await client.post(
        "/api/v1/stock-splits/", json=split1_data, headers={"Authorization": f"Bearer {auth_token}"}
    )

    # 3. 2回目の分割（2:1）
    split2_data = {
        "symbol": "8058",
        "split_date": "2024-12-01T00:00:00",
        "split_ratio": "2.0",
    }
    await client.post(
        "/api/v1/stock-splits/", json=split2_data, headers={"Authorization": f"Bearer {auth_token}"}
    )

    # 4. 調整値を確認（800株@1250円）
    response = await client.get(
        "/api/v1/transactions/?symbol=8058", headers={"Authorization": f"Bearer {auth_token}"}
    )
    transaction = response.json()[0]

    # 調整値は4 * 2 = 8倍
    assert Decimal(transaction["adjusted_quantity"]) == Decimal("800.0")  # 100 * 4 * 2
    assert Decimal(transaction["adjusted_price"]) == Decimal("1250.0")  # 10000 / 4 / 2
