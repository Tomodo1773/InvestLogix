import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_stock_split_and_recalculate(client: AsyncClient, db_session: AsyncSession, auth_user):
    """株式分割登録と過去取引の調整値再計算のテスト

    期待する動作:
    - 株式分割を登録すると、過去取引の調整値が自動的に再計算される
    - 分割比率4:1の場合、数量は4倍、価格は1/4になる

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_user: 認証済み一般ユーザーのフィクスチャ
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
    response = await client.post("/api/v1/transactions/", json=transaction_data)
    assert response.status_code == 200

    # 2. 4:1の株式分割を登録
    split_data = {
        "symbol": "8058",
        "split_date": "2024-06-01T00:00:00",
        "split_ratio": "4.0",
    }
    split_response = await client.post("/api/v1/stock-splits/", json=split_data)
    assert split_response.status_code == 201
    split_result = split_response.json()
    assert split_result["symbol"] == "8058"
    assert float(split_result["split_ratio"]) == 4.0

    # 3. 取引の調整値を確認（400株@2500円）
    transactions_response = await client.get("/api/v1/transactions/?symbol=8058")
    assert transactions_response.status_code == 200
    transactions = transactions_response.json()
    transaction = transactions[0]
    assert float(transaction["quantity"]) == 100.0  # 元の数量は変わらない
    assert float(transaction["price"]) == 10000.0  # 元の価格は変わらない
    assert float(transaction["adjusted_quantity"]) == 400.0  # 調整後: 100 * 4
    assert float(transaction["adjusted_price"]) == 2500.0  # 調整後: 10000 / 4


@pytest.mark.asyncio
async def test_holding_calculation_with_split(client: AsyncClient, db_session: AsyncSession, auth_user):
    """分割後の保有株計算が正しいことを確認

    期待する動作:
    - 分割前に100株@10000円で購入
    - 4:1分割を登録
    - 保有株情報が調整済み値で計算される（400株@2500円）

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_user: 認証済み一般ユーザーのフィクスチャ
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
    await client.post("/api/v1/transactions/", json=transaction_data)

    # 2. 4:1の株式分割を登録
    split_data = {
        "symbol": "8058",
        "split_date": "2024-06-01T00:00:00",
        "split_ratio": "4.0",
    }
    await client.post("/api/v1/stock-splits/", json=split_data)

    # 3. 保有株情報を取得して再計算
    recalc_response = await client.post("/api/v1/holdings/8058/recalculate")
    assert recalc_response.status_code == 200

    # 4. 保有株情報を確認
    holdings_response = await client.get("/api/v1/holdings/?symbol=8058")
    assert holdings_response.status_code == 200
    holdings = holdings_response.json()
    holding = holdings[0]

    # 数量=400株、平均取得単価=2500円であることを確認
    assert float(holding["quantity"]) == 400.0
    assert float(holding["average_cost"]) == 2500.0
    assert float(holding["total_cost"]) == 1000000.0  # 400 * 2500


@pytest.mark.asyncio
async def test_sell_after_split_realized_pl(client: AsyncClient, db_session: AsyncSession, auth_user):
    """分割後の売却時に正しい実現損益が計算されることを確認

    期待する動作:
    - 分割前に100株@10000円で購入
    - 4:1分割を登録
    - 分割後に200株@3000円で売却
    - 実現損益 = (3000 - 2500) * 200 = 100000円

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_user: 認証済み一般ユーザーのフィクスチャ
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
    await client.post("/api/v1/transactions/", json=buy_data)

    # 2. 4:1の株式分割を登録
    split_data = {
        "symbol": "8058",
        "split_date": "2024-06-01T00:00:00",
        "split_ratio": "4.0",
    }
    await client.post("/api/v1/stock-splits/", json=split_data)

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
    sell_response = await client.post("/api/v1/transactions/", json=sell_data)
    assert sell_response.status_code == 200
    sell_transaction = sell_response.json()

    # 4. 実現損益を確認: (3000 - 2500) * 200 = 100000円
    assert float(sell_transaction["realized_pl"]) == 100000.0

    # 5. 保有株情報を確認（残り200株）
    holdings_response = await client.get("/api/v1/holdings/?symbol=8058")
    holdings = holdings_response.json()
    holding = holdings[0]
    assert float(holding["quantity"]) == 200.0  # 400 - 200
    assert float(holding["realized_pl"]) == 100000.0


@pytest.mark.asyncio
async def test_recalculate_idempotency(client: AsyncClient, db_session: AsyncSession, auth_user):
    """調整値計算の冪等性を確認

    期待する動作:
    - 同じ計算を複数回実行しても結果が同じ

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_user: 認証済み一般ユーザーのフィクスチャ
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
    await client.post("/api/v1/transactions/", json=transaction_data)

    # 2. 株式分割を登録
    split_data = {
        "symbol": "8058",
        "split_date": "2024-06-01T00:00:00",
        "split_ratio": "4.0",
    }
    await client.post("/api/v1/stock-splits/", json=split_data)

    # 3. 1回目の取引情報取得
    response1 = await client.get("/api/v1/transactions/?symbol=8058")
    transaction1 = response1.json()[0]

    # 4. 再計算を実行
    await client.post("/api/v1/stock-splits/8058/recalculate")

    # 5. 2回目の取引情報取得
    response2 = await client.get("/api/v1/transactions/?symbol=8058")
    transaction2 = response2.json()[0]

    # 6. 1回目と2回目で調整値が同じであることを確認
    assert float(transaction1["adjusted_quantity"]) == float(transaction2["adjusted_quantity"])
    assert float(transaction1["adjusted_price"]) == float(transaction2["adjusted_price"])


@pytest.mark.asyncio
async def test_list_stock_splits_all(client: AsyncClient, db_session: AsyncSession, auth_user):
    """全銘柄の株式分割履歴取得のテスト

    期待する動作:
    - 複数の銘柄の分割情報を登録
    - 全銘柄の分割履歴を取得できる

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_user: 認証済み一般ユーザーのフィクスチャ
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
        await client.post("/api/v1/transactions/", json=transaction_data)

    # 1. 複数銘柄の分割情報を登録
    splits = [
        {"symbol": "8058", "split_date": "2024-06-01T00:00:00", "split_ratio": "4.0"},
        {"symbol": "7203", "split_date": "2024-07-01T00:00:00", "split_ratio": "5.0"},
    ]

    for split in splits:
        await client.post("/api/v1/stock-splits/", json=split)

    # 2. 全銘柄の分割履歴を取得
    response = await client.get("/api/v1/stock-splits/")
    assert response.status_code == 200
    result = response.json()

    # 3. 2件の分割情報が取得でき、銘柄名が含まれることを確認
    assert len(result) == 2
    for split in result:
        assert split["stock_name"] is not None


@pytest.mark.asyncio
async def test_list_stock_splits_by_symbol(client: AsyncClient, db_session: AsyncSession, auth_user):
    """特定銘柄の株式分割履歴取得のテスト

    期待する動作:
    - 複数の銘柄の分割情報を登録
    - 特定銘柄の分割履歴のみを取得できる

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_user: 認証済み一般ユーザーのフィクスチャ
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
        await client.post("/api/v1/transactions/", json=transaction_data)

    # 1. 複数銘柄の分割情報を登録
    splits = [
        {"symbol": "8058", "split_date": "2024-06-01T00:00:00", "split_ratio": "4.0"},
        {"symbol": "7203", "split_date": "2024-07-01T00:00:00", "split_ratio": "5.0"},
    ]

    for split in splits:
        await client.post("/api/v1/stock-splits/", json=split)

    # 2. 8058の分割履歴のみを取得
    response = await client.get("/api/v1/stock-splits/?symbol=8058")
    assert response.status_code == 200
    result = response.json()

    # 3. 1件のみ取得され、8058の情報と銘柄名が含まれることを確認
    assert len(result) == 1
    assert result[0]["symbol"] == "8058"
    assert float(result[0]["split_ratio"]) == 4.0
    assert result[0]["stock_name"] is not None


@pytest.mark.asyncio
async def test_delete_stock_split(client: AsyncClient, db_session: AsyncSession, auth_user):
    """株式分割削除のテスト

    期待する動作:
    - 分割情報を削除すると、調整値が再計算される（NULLに戻る）

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_user: 認証済み一般ユーザーのフィクスチャ
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
    await client.post("/api/v1/transactions/", json=transaction_data)

    # 2. 株式分割を登録
    split_data = {
        "symbol": "8058",
        "split_date": "2024-06-01T00:00:00",
        "split_ratio": "4.0",
    }
    split_response = await client.post("/api/v1/stock-splits/", json=split_data)
    split_id = split_response.json()["split_id"]

    # 3. 調整値が設定されていることを確認
    response_before = await client.get("/api/v1/transactions/?symbol=8058")
    transaction_before = response_before.json()[0]
    assert transaction_before["adjusted_quantity"] is not None
    assert transaction_before["adjusted_price"] is not None

    # 4. 分割情報を削除
    delete_response = await client.delete(f"/api/v1/stock-splits/{split_id}")
    assert delete_response.status_code == 204

    # 5. 調整値がNULLに戻っていることを確認
    response_after = await client.get("/api/v1/transactions/?symbol=8058")
    transaction_after = response_after.json()[0]
    assert transaction_after["adjusted_quantity"] is None
    assert transaction_after["adjusted_price"] is None


@pytest.mark.asyncio
async def test_multiple_splits(client: AsyncClient, db_session: AsyncSession, auth_user):
    """複数回の株式分割のテスト

    期待する動作:
    - 2回の分割（4:1と2:1）が正しく適用される
    - 最終的な調整値は両方の分割比率の積（8倍）になる

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_user: 認証済み一般ユーザーのフィクスチャ
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
    await client.post("/api/v1/transactions/", json=transaction_data)

    # 2. 1回目の分割（4:1）
    split1_data = {
        "symbol": "8058",
        "split_date": "2024-06-01T00:00:00",
        "split_ratio": "4.0",
    }
    await client.post("/api/v1/stock-splits/", json=split1_data)

    # 3. 2回目の分割（2:1）
    split2_data = {
        "symbol": "8058",
        "split_date": "2024-12-01T00:00:00",
        "split_ratio": "2.0",
    }
    await client.post("/api/v1/stock-splits/", json=split2_data)

    # 4. 調整値を確認（800株@1250円）
    response = await client.get("/api/v1/transactions/?symbol=8058")
    transaction = response.json()[0]

    # 調整値は4 * 2 = 8倍
    assert float(transaction["adjusted_quantity"]) == 800.0  # 100 * 4 * 2
    assert float(transaction["adjusted_price"]) == 1250.0  # 10000 / 4 / 2


@pytest.mark.asyncio
async def test_create_stock_split_rejects_duplicate(client: AsyncClient, db_session: AsyncSession, auth_user):
    """同一銘柄・同一分割基準日の重複登録が拒否されることを確認

    期待する動作:
    - 2回目の登録は409 Conflictになる
    - 重複登録によって調整値に分割比率が二重に掛からない

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_user: 認証済み一般ユーザーのフィクスチャ
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
    await client.post("/api/v1/transactions/", json=transaction_data)

    split_data = {
        "symbol": "8058",
        "split_date": "2024-06-01T00:00:00",
        "split_ratio": "4.0",
    }

    # 2. 1回目の登録は成功する
    first_response = await client.post("/api/v1/stock-splits/", json=split_data)
    assert first_response.status_code == 201

    # 3. 2回目の登録は409になる
    second_response = await client.post("/api/v1/stock-splits/", json=split_data)
    assert second_response.status_code == 409

    # 4. 分割は1件のみ登録され、調整値は4倍のまま（二重適用されていない）
    splits_response = await client.get("/api/v1/stock-splits/?symbol=8058")
    assert len(splits_response.json()) == 1

    transactions_response = await client.get("/api/v1/transactions/?symbol=8058")
    transaction = transactions_response.json()[0]
    assert float(transaction["adjusted_quantity"]) == 400.0
    assert float(transaction["adjusted_price"]) == 2500.0


@pytest.mark.asyncio
async def test_create_stock_split_rejects_unknown_symbol(
    client: AsyncClient, db_session: AsyncSession, auth_user
):
    """銘柄マスターに未登録の銘柄コードが拒否されることを確認

    期待する動作:
    - 取引実績のない銘柄コードでは404 Not Foundになる

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_user: 認証済み一般ユーザーのフィクスチャ
    """
    split_data = {
        "symbol": "9999",
        "split_date": "2024-06-01T00:00:00",
        "split_ratio": "4.0",
    }
    response = await client.post("/api/v1/stock-splits/", json=split_data)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_stock_split_rejects_non_positive_ratio(
    client: AsyncClient, db_session: AsyncSession, auth_user
):
    """0以下の分割比率が拒否されることを確認

    期待する動作:
    - 比率0はゼロ除算を招くため422 Unprocessable Entityになる
    - 負の比率も422になる

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_user: 認証済み一般ユーザーのフィクスチャ
    """
    for invalid_ratio in ("0.0", "-2.0"):
        response = await client.post(
            "/api/v1/stock-splits/",
            json={
                "symbol": "8058",
                "split_date": "2024-06-01T00:00:00",
                "split_ratio": invalid_ratio,
            },
        )
        assert response.status_code == 422, f"split_ratio={invalid_ratio}"
