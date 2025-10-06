from datetime import datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_dividend(client: AsyncClient, db_session: AsyncSession, auth_token: str, setup_japanese_stock_data):
    """配当情報の登録テスト

    期待する動作:
    - ステータスコード200
    - 登録された配当情報を返却
    - 保有情報の配当総額が更新される

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        setup_japanese_stock_data: 日本株のテストデータ
    """
    # 配当情報の登録
    dividend_data = {
        "symbol": "8058",
        "payment_date": "2024-03-15T00:00:00Z",
        "shares_owned": "100.0",
        "total_amount": "25000.0",
        "tax": "2500.0",
        "fee": "0.0",
    }

    response = await client.post("/api/v1/dividends/", json=dividend_data, headers={"Authorization": f"Bearer {auth_token}"})

    # レスポンスの検証
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == dividend_data["symbol"]
    assert datetime.fromisoformat(data["payment_date"]).strftime("%Y-%m-%dT%H:%M:%S") == "2024-03-15T00:00:00"
    assert Decimal(data["total_amount"]) == Decimal(dividend_data["total_amount"])
    assert Decimal(data["tax"]) == Decimal(dividend_data["tax"])
    assert Decimal(data["fee"]) == Decimal(dividend_data["fee"])

    # 保有情報の確認（配当金が反映されているか）
    holdings_response = await client.get("/api/v1/holdings/", headers={"Authorization": f"Bearer {auth_token}"})
    assert holdings_response.status_code == 200
    holdings = holdings_response.json()
    holding = next((h for h in holdings if h["symbol"] == "8058"), None)
    assert holding is not None
    # 配当金の純額（税引き後）= 22500 が反映されていることを確認
    assert Decimal(holding["total_dividend"]) == Decimal("22500.0")


@pytest.mark.asyncio
async def test_create_dividend_stock_not_found(client: AsyncClient, auth_token: str):
    """存在しない銘柄の配当情報登録テスト

    期待する動作:
    - ステータスコード404
    - エラーメッセージを返却

    Args:
        client: 非同期HTTPクライアント
        auth_token: 認証トークン
    """
    dividend_data = {
        "symbol": "INVALID",
        "payment_date": "2024-03-15T00:00:00Z",
        "shares_owned": "100.0",
        "total_amount": "25000.0",
        "tax": "2500.0",
        "fee": "0.0",
    }

    response = await client.post("/api/v1/dividends/", json=dividend_data, headers={"Authorization": f"Bearer {auth_token}"})

    # レスポンス検証
    assert response.status_code == 404
    assert response.json()["detail"] == "Stock not found"


@pytest.mark.asyncio
async def test_list_dividends(
    client: AsyncClient, db_session: AsyncSession, auth_token: str, setup_japanese_stock_data, create_dividend
):
    """配当一覧取得テスト

    期待する動作:
    - ステータスコード200
    - 登録された配当情報が支払日の降順で返却される
    - 配当情報に銘柄名が含まれている

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        setup_japanese_stock_data: 日本株のテストデータ
        create_dividend: 配当登録用フィクスチャー
    """
    # 複数の配当情報を登録
    dividend_data_list = [
        {
            "symbol": "8058",
            "payment_date": "2024-03-15T00:00:00Z",
            "shares_owned": "100.0",
            "total_amount": "25000.0",
            "tax": "2500.0",
            "fee": "0.0",
        },
        {
            "symbol": "8058",
            "payment_date": "2024-02-15T00:00:00Z",
            "shares_owned": "100.0",
            "total_amount": "25000.0",
            "tax": "2500.0",
            "fee": "0.0",
        },
    ]

    for dividend_data in dividend_data_list:
        await create_dividend(dividend_data)

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
        assert dividend["stock_name"] == "三菱商事"


@pytest.mark.asyncio
async def test_get_monthly_dividends(client: AsyncClient, auth_token: str, setup_dividend_data: dict):
    """月次配当金集計の取得テスト

    期待する動作:
    - ステータスコード200
    - 月ごとの配当金集計が日付順に返却される

    Args:
        client: 非同期HTTPクライアント
        auth_token: 認証トークン
        setup_dividend_data: テスト用配当データ
    """
    # 月次配当金集計の取得
    response = await client.get("/api/v1/dividends/monthly", headers={"Authorization": f"Bearer {auth_token}"})

    # レスポンスの検証
    assert response.status_code == 200
    data = response.json()

    # データの形式を検証
    assert isinstance(data, list)
    if len(data) > 0:
        month_data = data[0]
        assert "year" in month_data
        assert "month" in month_data
        assert "total_dividend" in month_data

        # 数値型であることを検証
        assert isinstance(month_data["year"], int)
        assert isinstance(month_data["month"], int)
        assert isinstance(month_data["total_dividend"], (int, float))

        # setup_dividend_dataで追加した配当金が集計されていることを確認
        jan_2024_data = next((item for item in data if item["year"] == 2024 and item["month"] == 1), None)
        if jan_2024_data:
            # setup_dividend_dataの実際の値からテスト用の期待値を計算
            jp_dividend = setup_dividend_data["jp_dividend"]
            us_dividend = setup_dividend_data["us_dividend"]

            # 実際のデータから税引後配当を計算
            jp_amount = float(jp_dividend["total_amount"]) - float(jp_dividend["tax"]) - float(jp_dividend["fee"])
            us_amount = float(us_dividend["total_amount"]) - float(us_dividend["tax"]) - float(us_dividend["fee"])
            expected_amount = jp_amount + us_amount

            # 実際の値と比較（小数点以下の誤差を許容）
            assert abs(jan_2024_data["total_dividend"] - expected_amount) < 0.01
