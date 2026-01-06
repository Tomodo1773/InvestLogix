"""APIレスポンスの日時がJSTで返されることを確認するテスト"""

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_transaction_response_datetime_is_jst(
    client: AsyncClient, db_session: AsyncSession, auth_token: str
):
    """取引APIのレスポンスの日時がJST ISO形式であること

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # 取引データを登録（naive datetimeで送信）
    transaction_data = {
        "symbol": "8058",
        "transaction_type": "buy",
        "quantity": "10.0",
        "price": "3000.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-06-15T10:30:00",  # naive datetime
    }

    response = await client.post(
        "/api/v1/transactions/", json=transaction_data, headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    # レスポンスの日時がJST形式（+09:00）であること
    assert "+09:00" in data["transaction_date"]

    # パースして正しい時刻であることを確認
    parsed_dt = datetime.fromisoformat(data["transaction_date"])
    assert parsed_dt.tzinfo is not None
    assert parsed_dt.hour == 10
    assert parsed_dt.minute == 30


@pytest.mark.asyncio
async def test_transaction_list_response_datetime_is_jst(
    client: AsyncClient, db_session: AsyncSession, auth_token: str
):
    """取引一覧APIのレスポンスの日時がJST ISO形式であること

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # 取引データを登録
    transaction_data = {
        "symbol": "8058",
        "transaction_type": "buy",
        "quantity": "10.0",
        "price": "3000.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-06-15T10:30:00",
    }
    await client.post(
        "/api/v1/transactions/", json=transaction_data, headers={"Authorization": f"Bearer {auth_token}"}
    )

    # 取引一覧を取得
    response = await client.get("/api/v1/transactions/", headers={"Authorization": f"Bearer {auth_token}"})

    assert response.status_code == 200
    data = response.json()

    # 全ての取引の日時がJST形式であること
    for transaction in data:
        assert "+09:00" in transaction["transaction_date"]


@pytest.mark.asyncio
async def test_dividend_response_datetime_is_jst(
    client: AsyncClient, db_session: AsyncSession, auth_token: str, setup_japanese_stock_data
):
    """配当APIのレスポンスの日時がJST ISO形式であること

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        setup_japanese_stock_data: 日本株のテストデータ
    """
    # 配当データを登録（naive datetimeで送信）
    dividend_data = {
        "symbol": "8058",
        "payment_date": "2024-03-15T00:00:00",  # naive datetime
        "shares_owned": "100.0",
        "total_amount": "25000.0",
        "tax": "2500.0",
        "fee": "0.0",
    }

    response = await client.post(
        "/api/v1/dividends/", json=dividend_data, headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    # レスポンスの日時がJST形式（+09:00）であること
    assert "+09:00" in data["payment_date"]

    # パースして正しい時刻であることを確認
    parsed_dt = datetime.fromisoformat(data["payment_date"])
    assert parsed_dt.tzinfo is not None
    assert parsed_dt.day == 15
    assert parsed_dt.month == 3


@pytest.mark.asyncio
async def test_dividend_list_response_datetime_is_jst(
    client: AsyncClient, db_session: AsyncSession, auth_token: str, setup_japanese_stock_data, create_dividend
):
    """配当一覧APIのレスポンスの日時がJST ISO形式であること

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        setup_japanese_stock_data: 日本株のテストデータ
        create_dividend: 配当登録用フィクスチャー
    """
    # 配当データを登録
    dividend_data = {
        "symbol": "8058",
        "payment_date": "2024-03-15T00:00:00",
        "shares_owned": "100.0",
        "total_amount": "25000.0",
        "tax": "2500.0",
        "fee": "0.0",
    }
    await create_dividend(dividend_data)

    # 配当一覧を取得
    response = await client.get("/api/v1/dividends/", headers={"Authorization": f"Bearer {auth_token}"})

    assert response.status_code == 200
    data = response.json()

    # 全ての配当の日時がJST形式であること
    for dividend in data:
        assert "+09:00" in dividend["payment_date"]


@pytest.mark.asyncio
async def test_holdings_response_datetime_is_jst(
    client: AsyncClient, db_session: AsyncSession, auth_token: str, setup_japanese_stock_data
):
    """保有株APIのレスポンスの日時がJST ISO形式であること

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        setup_japanese_stock_data: 日本株のテストデータ
    """
    # 保有株一覧を取得
    response = await client.get("/api/v1/holdings/", headers={"Authorization": f"Bearer {auth_token}"})

    assert response.status_code == 200
    data = response.json()

    # 全ての保有株のlast_updatedがJST形式であること
    for holding in data:
        assert "+09:00" in holding["last_updated"]


@pytest.mark.asyncio
async def test_transaction_monthly_summary_uses_jst(
    client: AsyncClient, db_session: AsyncSession, auth_token: str
):
    """月次取引集計がJST基準で集計されること

    JST 2024-12-01 00:00:00（= UTC 2024-11-30 15:00:00）の取引が
    12月として集計されることを確認する。

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # JST 12/1 0:00 の取引を登録（JSTタイムゾーン付きで送信）
    transaction_data = {
        "symbol": "8058",
        "transaction_type": "buy",
        "quantity": "10.0",
        "price": "3000.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-12-01T00:00:00+09:00",  # JST
    }

    response = await client.post(
        "/api/v1/transactions/", json=transaction_data, headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200

    # 月次集計を取得
    monthly_response = await client.get(
        "/api/v1/transactions/monthly", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert monthly_response.status_code == 200
    data = monthly_response.json()

    # 12月のデータが存在すること
    dec_entry = next((item for item in data if item["year"] == 2024 and item["month"] == 12), None)
    assert dec_entry is not None

    # 11月のデータが存在しないこと（UTC基準なら11月に入ってしまう）
    nov_entry = next((item for item in data if item["year"] == 2024 and item["month"] == 11), None)
    assert nov_entry is None


@pytest.mark.asyncio
async def test_transaction_yearly_summary_uses_jst(
    client: AsyncClient, db_session: AsyncSession, auth_token: str
):
    """年次取引集計がJST基準で集計されること

    JST 2024-01-01 00:00:00（= UTC 2023-12-31 15:00:00）の取引が
    2024年として集計されることを確認する。

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
    """
    # JST 2024/1/1 0:00 の取引を登録（JSTタイムゾーン付きで送信）
    transaction_data = {
        "symbol": "8058",
        "transaction_type": "buy",
        "quantity": "10.0",
        "price": "3000.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00+09:00",  # JST
    }

    response = await client.post(
        "/api/v1/transactions/", json=transaction_data, headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200

    # 年次集計を取得
    yearly_response = await client.get(
        "/api/v1/transactions/yearly", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert yearly_response.status_code == 200
    data = yearly_response.json()

    # 2024年のデータが存在すること
    year_2024_entry = next((item for item in data if item["year"] == 2024), None)
    assert year_2024_entry is not None

    # 2023年のデータが存在しないこと（UTC基準なら2023年に入ってしまう）
    year_2023_entry = next((item for item in data if item["year"] == 2023), None)
    assert year_2023_entry is None
