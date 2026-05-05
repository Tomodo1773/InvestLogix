import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_buy_transaction(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """株式購入取引の登録テスト

    期待する動作:
    - ステータスコード200
    - 登録された取引情報を返却
    - ホールディングテーブルに保有情報が正しく反映されていること

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # テストデータ準備
    transaction_data = {
        "symbol": "8058",
        "transaction_type": "buy",
        "quantity": "10.0",
        "price": "3000.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }

    # APIリクエスト実行
    response = await client.post("/api/v1/transactions/", json=transaction_data)

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "8058"
    assert data["transaction_type"] == "buy"
    assert float(data["quantity"]) == 10.0
    assert float(data["price"]) == 3000.0

    # ホールディングテーブルの状態を確認（指定銘柄のみ）
    holdings_response = await client.get("/api/v1/holdings/?symbol=8058")
    assert holdings_response.status_code == 200
    holdings = holdings_response.json()
    holding = holdings[0]
    assert holding["symbol"] == "8058"
    assert float(holding["quantity"]) == 10.0  # トランザクションで登録した数量と一致すること
    assert float(holding["average_cost"]) == 3000.0  # 平均取得単価が正しいこと
    assert float(holding["total_cost"]) == 30000.0  # 総取得価額が正しいこと


@pytest.mark.asyncio
async def test_create_sell_transaction(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """株式売却取引の登録テスト

    期待する動作:
    - ステータスコード200
    - 登録された取引情報を返却

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # 事前に購入取引を登録
    buy_transaction = {
        "symbol": "8058",
        "transaction_type": "buy",
        "quantity": "10.0",
        "price": "3000.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }
    await client.post("/api/v1/transactions/", json=buy_transaction)

    # 売却取引のテストデータ準備
    transaction_data = {
        "symbol": "8058",
        "transaction_type": "sell",
        "quantity": "5.0",
        "price": "3500.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }

    # APIリクエスト実行
    response = await client.post("/api/v1/transactions/", json=transaction_data)

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "8058"
    assert data["transaction_type"] == "sell"
    assert float(data["quantity"]) == 5.0
    assert float(data["price"]) == 3500.0

    # 売却後のホールディングの実現損益を確認
    holdings_response = await client.get("/api/v1/holdings/?symbol=8058")
    assert holdings_response.status_code == 200
    holdings = holdings_response.json()
    holding = holdings[0]
    assert float(holding["realized_pl"]) == 2500.0


@pytest.mark.asyncio
async def test_create_transaction_insufficient_shares(
    client: AsyncClient, db_session: AsyncSession, auth_token: str
):
    """保有株数不足による売却取引の失敗テスト

    期待する動作:
    - ステータスコード400
    - エラーメッセージを返却

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # 売却取引のテストデータ準備（保有数量ゼロで売却）
    transaction_data = {
        "symbol": "8058",
        "transaction_type": "sell",
        "quantity": "100.0",
        "price": "3500.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }

    # APIリクエスト実行
    response = await client.post("/api/v1/transactions/", json=transaction_data)

    # レスポンス検証
    assert response.status_code == 400
    assert response.json()["detail"] == "Insufficient shares"


@pytest.mark.asyncio
async def test_create_transaction_stock_not_found(
    client: AsyncClient, db_session: AsyncSession, auth_token: str
):
    """存在しない銘柄による取引の失敗テスト

    期待する動作:
    - ステータスコード404
    - エラーメッセージを返却

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # テストデータ準備
    transaction_data = {
        "symbol": "INVALID",
        "transaction_type": "buy",
        "quantity": "10.0",
        "price": "3000.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }

    # APIリクエスト実行
    response = await client.post("/api/v1/transactions/", json=transaction_data)

    # レスポンス検証
    assert response.status_code == 404
    assert response.json()["detail"] == "Stock not found"


@pytest.mark.asyncio
async def test_multiple_buy_transactions_average_cost(
    client: AsyncClient, db_session: AsyncSession, auth_token: str
):
    """複数回の購入取引による平均取得単価の計算テスト

    期待する動作:
    - 1回目の購入: 10株@3000円
    - 2回目の購入: 5株@4000円
    - 保有数量: 15株
    - 平均取得単価: ((10 * 3000) + (5 * 4000)) / 15 = 3333.33...円

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # 1回目の購入取引データ準備（10株@3000円）
    first_buy = {
        "symbol": "8058",
        "transaction_type": "buy",
        "quantity": "10.0",
        "price": "3000.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }
    await client.post("/api/v1/transactions/", json=first_buy)

    # 2回目の購入取引データ準備（5株@4000円）
    second_buy = {
        "symbol": "8058",
        "transaction_type": "buy",
        "quantity": "5.0",
        "price": "4000.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-02T00:00:00",
    }
    await client.post("/api/v1/transactions/", json=second_buy)

    # ポートフォリオから保有情報を取得して確認
    holdings_response = await client.get("/api/v1/holdings/")
    assert holdings_response.status_code == 200
    holdings = holdings_response.json()

    # 指定した銘柄の保有情報を検索
    holding = next((h for h in holdings if h["symbol"] == "8058"), None)
    assert holding is not None
    assert float(holding["quantity"]) == 15.0
    assert abs(float(holding["average_cost"]) - 3333.33) < 0.01
    assert abs(float(holding["total_cost"]) - 50000.00) < 0.01


@pytest.mark.asyncio
async def test_buy_and_partial_sell_calculation(
    client: AsyncClient, db_session: AsyncSession, auth_token: str
):
    """購入後の一部売却時の売却益と保有株数の計算テスト

    期待する動作:
    - 1回目の購入: 100株@1000円 = 100,000円
    - 一部売却: 60株@1500円
        - 売却益: (1500円 - 1000円) * 60株 = 30,000円
        - 残り保有数: 40株
        - 平均取得単価: 1000円（変化なし）
        - 残りの取得価額合計: 1000円 * 40株 = 40,000円

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # 購入取引データ準備（100株@1000円）
    buy_transaction = {
        "symbol": "7203",
        "transaction_type": "buy",
        "quantity": "100.0",
        "price": "1000.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }
    await client.post("/api/v1/transactions/", json=buy_transaction)

    # 一部売却取引データ準備（60株@1500円）
    sell_transaction = {
        "symbol": "7203",
        "transaction_type": "sell",
        "quantity": "60.0",
        "price": "1500.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-02T00:00:00",
    }
    await client.post("/api/v1/transactions/", json=sell_transaction)

    # ポートフォリオから保有情報を取得して確認
    holdings_response = await client.get("/api/v1/holdings/")
    assert holdings_response.status_code == 200
    holdings = holdings_response.json()

    # 指定した銘柄の保有情報を検索
    holding = next((h for h in holdings if h["symbol"] == "7203"), None)
    assert holding is not None

    # 保有数量の確認（100株 - 60株 = 40株）
    assert float(holding["quantity"]) == 40.0

    # 平均取得単価の確認（1000円のまま変化なし）
    assert float(holding["average_cost"]) == 1000.0

    # 取得価額合計の確認（1000円 * 40株 = 40,000円）
    assert float(holding["total_cost"]) == 40000.0

    # 売却益の確認（(1500円 - 1000円) * 60株 = 30,000円）
    assert float(holding["realized_pl"]) == 30000.0


@pytest.mark.asyncio
async def test_create_transaction_with_usd_price(
    client: AsyncClient, db_session: AsyncSession, auth_token: str, mock_external_apis
):
    """USD価格を含む取引の登録テスト

    期待する動作:
    - ステータスコード200
    - 登録された取引情報を返却（USD価格を含む）
    - AlphaVantage APIが適切に呼び出されること

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        mock_external_apis: モック化されたAPI
    """
    # テストデータ準備
    transaction_data = {
        "symbol": "AAPL",
        "transaction_type": "buy",
        "quantity": "10.0",
        "price": "20000.0",
        "usd_price": "135.67",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }

    # APIリクエスト実行
    response = await client.post("/api/v1/transactions/", json=transaction_data)

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert float(data["price"]) == 20000.0
    assert float(data["usd_price"]) == 135.67

    # モックが呼び出されたことを確認
    mock_external_apis["overview"].assert_called_once_with("AAPL")


@pytest.mark.asyncio
async def test_list_transactions(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """取引履歴取得を確認するテスト

    期待する動作:
    - ステータスコード200
    - 取引情報に銘柄名が含まれている

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # 事前に購入取引を登録
    transaction_data = {
        "symbol": "8058",
        "transaction_type": "buy",
        "quantity": "10.0",
        "price": "3000.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }
    await client.post("/api/v1/transactions/", json=transaction_data)

    # 取引履歴を取得
    response = await client.get("/api/v1/transactions/")

    # レスポンスの検証
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["stock_name"] == "三菱商事"


@pytest.mark.asyncio
async def test_list_transactions_with_unrealized_pl(
    client: AsyncClient, db_session: AsyncSession, auth_token: str
):
    """買付取引に未実現損益を含めて取得するテスト

    期待する動作:
    - include_unrealized_pl=trueかつsymbol指定時、買付取引に未実現損益が含まれる
    - 売却取引には未実現損益が含まれない（null）

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # 事前に購入取引を登録
    buy_transaction = {
        "symbol": "8058",
        "transaction_type": "buy",
        "quantity": "10.0",
        "price": "3000.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }
    await client.post("/api/v1/transactions/", json=buy_transaction)

    # 売却取引を登録
    sell_transaction = {
        "symbol": "8058",
        "transaction_type": "sell",
        "quantity": "5.0",
        "price": "3500.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-02T00:00:00",
    }
    await client.post("/api/v1/transactions/", json=sell_transaction)

    # 未実現損益を含めて取引履歴を取得
    response = await client.get(
        "/api/v1/transactions/?symbol=8058&include_unrealized_pl=true",
    )

    # レスポンスの検証
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # 日付降順で返されるので、売却が先
    sell_data = data[0]  # 売却取引
    buy_data = data[1]  # 買付取引

    # 売却取引には未実現損益がnull
    assert sell_data["transaction_type"] == "sell"
    assert sell_data["unrealized_pl"] is None
    assert sell_data["unrealized_pl_percentage"] is None

    # 買付取引には未実現損益が含まれる
    assert buy_data["transaction_type"] == "buy"
    assert buy_data["unrealized_pl"] is not None
    assert buy_data["unrealized_pl_percentage"] is not None


@pytest.mark.asyncio
async def test_list_transactions_without_unrealized_pl(
    client: AsyncClient, db_session: AsyncSession, auth_token: str
):
    """include_unrealized_pl未指定時のテスト（デフォルトはfalse）

    期待する動作:
    - パラメータ未指定時は従来通りの動作（損益情報なし）

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # 事前に購入取引を登録
    transaction_data = {
        "symbol": "8058",
        "transaction_type": "buy",
        "quantity": "10.0",
        "price": "3000.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }
    await client.post("/api/v1/transactions/", json=transaction_data)

    # include_unrealized_plを指定せずに取引履歴を取得
    response = await client.get(
        "/api/v1/transactions/?symbol=8058",
    )

    # レスポンスの検証
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

    # 未実現損益フィールドがレスポンスに含まれていないことを確認
    assert "unrealized_pl" not in data[0]
    assert "unrealized_pl_percentage" not in data[0]
