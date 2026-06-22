from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_dividend(
    client: AsyncClient, db_session: AsyncSession, auth_token: str, setup_japanese_stock_data
):
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

    response = await client.post("/api/v1/dividends/", json=dividend_data)

    # レスポンスの検証
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == dividend_data["symbol"]
    # レスポンスがJST形式（+09:00）であることを確認
    assert "+09:00" in data["payment_date"]
    parsed_dt = datetime.fromisoformat(data["payment_date"])
    # UTC 2024-03-15T00:00:00Z → JST 2024-03-15T09:00:00+09:00
    assert parsed_dt.strftime("%Y-%m-%dT%H:%M:%S") == "2024-03-15T09:00:00"
    assert float(data["total_amount"]) == float(dividend_data["total_amount"])
    assert float(data["tax"]) == float(dividend_data["tax"])
    assert float(data["fee"]) == float(dividend_data["fee"])

    # 保有情報の確認（配当金が反映されているか）
    holdings_response = await client.get("/api/v1/holdings/")
    assert holdings_response.status_code == 200
    holdings = holdings_response.json()
    holding = next((h for h in holdings if h["symbol"] == "8058"), None)
    assert holding is not None
    # 配当金の純額（税引き後）= 22500 が反映されていることを確認
    assert float(holding["total_dividend"]) == 22500.0


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

    response = await client.post("/api/v1/dividends/", json=dividend_data)

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
    response = await client.get("/api/v1/dividends/")

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
        assert float(dividend["total_amount"]) == 25000.0
        assert float(dividend["tax"]) == 2500.0
        assert float(dividend["fee"]) == 0.0
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
    response = await client.get("/api/v1/dividends/monthly")

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
            jp_amount = (
                float(jp_dividend["total_amount"]) - float(jp_dividend["tax"]) - float(jp_dividend["fee"])
            )
            us_amount = (
                float(us_dividend["total_amount"]) - float(us_dividend["tax"]) - float(us_dividend["fee"])
            )
            expected_amount = jp_amount + us_amount

            # 実際の値と比較（小数点以下の誤差を許容）
            assert abs(jan_2024_data["total_dividend"] - expected_amount) < 0.01


@pytest.mark.asyncio
async def test_get_dividends_by_symbol(client: AsyncClient, auth_token: str, setup_dividend_data: dict):
    """銘柄別配当金集計の取得テスト

    期待する動作:
    - ステータスコード200
    - 銘柄ごとに税引後の配当金が合算される
    - 配当金額の降順で返却される
    - 各要素に銘柄コード・銘柄名・配当金額が含まれる

    Args:
        client: 非同期HTTPクライアント
        auth_token: 認証トークン
        setup_dividend_data: テスト用配当データ（JP: 8058, US: AAPL）
    """
    response = await client.get("/api/v1/dividends/by-symbol")

    assert response.status_code == 200
    data = response.json()

    # 2銘柄分の集計が返ること
    assert len(data) == 2

    # 税引後の期待値を計算
    jp_dividend = setup_dividend_data["jp_dividend"]
    us_dividend = setup_dividend_data["us_dividend"]
    jp_amount = float(jp_dividend["total_amount"]) - float(jp_dividend["tax"]) - float(jp_dividend["fee"])
    us_amount = float(us_dividend["total_amount"]) - float(us_dividend["tax"]) - float(us_dividend["fee"])

    # 金額降順（US: 2400 > JP: 1600）で返ること
    assert data[0]["symbol"] == "AAPL"
    assert abs(data[0]["total_dividend"] - us_amount) < 0.01
    assert data[1]["symbol"] == "8058"
    assert abs(data[1]["total_dividend"] - jp_amount) < 0.01

    # 銘柄名が含まれること
    for item in data:
        assert isinstance(item["stock_name"], str)
        assert item["stock_name"]


@pytest.mark.asyncio
async def test_get_dividends_by_symbol_aggregates_multiple_payments(
    client: AsyncClient, auth_token: str, setup_japanese_stock_data, create_dividend
):
    """同一銘柄の複数回配当が1件に合算されることを確認する"""
    await create_dividend(
        {
            "symbol": "8058",
            "payment_date": "2024-01-15T00:00:00+09:00",
            "shares_owned": "100.0",
            "total_amount": "1000.0",
            "tax": "100.0",
            "fee": "0.0",
        }
    )
    await create_dividend(
        {
            "symbol": "8058",
            "payment_date": "2024-06-15T00:00:00+09:00",
            "shares_owned": "100.0",
            "total_amount": "2000.0",
            "tax": "200.0",
            "fee": "0.0",
        }
    )

    response = await client.get("/api/v1/dividends/by-symbol")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["symbol"] == "8058"
    # (1000-100) + (2000-200) = 2700
    assert abs(data[0]["total_dividend"] - 2700.0) < 0.01


@pytest.mark.asyncio
async def test_get_monthly_dividends_respects_jst_boundary(
    client: AsyncClient, auth_token: str, create_dividend
):
    """JST 月初0時の配当が正しく当月に集計されることを確認する

    このテストは、タイムゾーン境界でのエッジケースを検証します:
    - JST で 2024-12-01 00:00:00 は UTC では 2024-11-30 15:00:00
    - UTC 基準で集計すると 11月に誤って集計される可能性がある
    - JST 基準で正しく 12月に集計されることを確認する
    """
    boundary_dividend = {
        "symbol": "8058",
        "payment_date": "2024-12-01T00:00:00+09:00",  # JST で 12/1 0:00 は UTC では 11/30 15:00
        "shares_owned": "50.0",
        "total_amount": "3000.0",
        "tax": "300.0",
        "fee": "0.0",
    }
    await create_dividend(boundary_dividend)

    response = await client.get("/api/v1/dividends/monthly")
    assert response.status_code == 200
    data = response.json()

    dec_entry = next((item for item in data if item["year"] == 2024 and item["month"] == 12), None)
    assert dec_entry is not None
    expected_amount = 3000.0 - 300.0
    assert abs(dec_entry["total_dividend"] - expected_amount) < 0.01

    # UTC 基準で集計されている場合に誤って 11 月へ入らないことを検証
    nov_entry = next((item for item in data if item["year"] == 2024 and item["month"] == 11), None)
    assert nov_entry is None


@pytest.mark.asyncio
async def test_get_monthly_dividends_fills_gaps(client: AsyncClient, auth_token: str, create_dividend):
    """配当がない月も total_dividend: 0 で補完されることを確認する"""
    # 2024年1月と3月にデータを登録（2月は欠落）
    await create_dividend(
        {
            "symbol": "8058",
            "payment_date": "2024-01-15T00:00:00+09:00",
            "shares_owned": "100.0",
            "total_amount": "1000.0",
            "tax": "100.0",
            "fee": "0.0",
        }
    )
    await create_dividend(
        {
            "symbol": "8058",
            "payment_date": "2024-03-15T00:00:00+09:00",
            "shares_owned": "100.0",
            "total_amount": "2000.0",
            "tax": "200.0",
            "fee": "0.0",
        }
    )

    response = await client.get(
        "/api/v1/dividends/monthly",
    )
    assert response.status_code == 200
    data = response.json()

    # 1月、2月、3月の3件が返ること
    assert len(data) == 3
    assert data[0] == {"year": 2024, "month": 1, "total_dividend": 900.0}
    assert data[1] == {"year": 2024, "month": 2, "total_dividend": 0.0}
    assert data[2] == {"year": 2024, "month": 3, "total_dividend": 1800.0}


@pytest.mark.asyncio
async def test_get_dividends_by_symbol_with_year_month(
    client: AsyncClient, auth_token: str, setup_japanese_stock_data, create_dividend
):
    """特定月を指定すると、その月のみの銘柄別集計が返ること"""
    await create_dividend(
        {
            "symbol": "8058",
            "payment_date": "2024-01-15T00:00:00+09:00",
            "shares_owned": "100.0",
            "total_amount": "1000.0",
            "tax": "100.0",
            "fee": "0.0",
        }
    )
    await create_dividend(
        {
            "symbol": "8058",
            "payment_date": "2024-06-15T00:00:00+09:00",
            "shares_owned": "100.0",
            "total_amount": "2000.0",
            "tax": "200.0",
            "fee": "0.0",
        }
    )

    response = await client.get("/api/v1/dividends/by-symbol?year=2024&month=1")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["symbol"] == "8058"
    # 1000 - 100 = 900
    assert abs(data[0]["total_dividend"] - 900.0) < 0.01


@pytest.mark.asyncio
async def test_get_dividends_by_symbol_empty_month(
    client: AsyncClient, auth_token: str, setup_japanese_stock_data, create_dividend
):
    """配当がない月を指定すると空配列が返ること"""
    await create_dividend(
        {
            "symbol": "8058",
            "payment_date": "2024-01-15T00:00:00+09:00",
            "shares_owned": "100.0",
            "total_amount": "1000.0",
            "tax": "100.0",
            "fee": "0.0",
        }
    )

    response = await client.get("/api/v1/dividends/by-symbol?year=2024&month=7")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


@pytest.mark.asyncio
async def test_get_dividends_by_symbol_partial_params(client: AsyncClient, auth_token: str):
    """yearのみ/monthのみ指定で422が返ること"""
    response = await client.get("/api/v1/dividends/by-symbol?year=2024")
    assert response.status_code == 422

    response = await client.get("/api/v1/dividends/by-symbol?month=1")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_dividends_by_symbol_jst_boundary(client: AsyncClient, auth_token: str, create_dividend):
    """JST月境界で正しくフィルタリングされること"""
    # JST 2024-12-01 00:00:00 = UTC 2024-11-30 15:00:00
    await create_dividend(
        {
            "symbol": "8058",
            "payment_date": "2024-12-01T00:00:00+09:00",
            "shares_owned": "50.0",
            "total_amount": "3000.0",
            "tax": "300.0",
            "fee": "0.0",
        }
    )

    # JST基準で12月に集計されること
    response = await client.get("/api/v1/dividends/by-symbol?year=2024&month=12")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert abs(data[0]["total_dividend"] - 2700.0) < 0.01

    # 11月には含まれないこと
    response = await client.get("/api/v1/dividends/by-symbol?year=2024&month=11")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0
