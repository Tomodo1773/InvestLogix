from decimal import Decimal

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def setup_portfolio_test_data(
    setup_japanese_stock_data,
    setup_us_stock_data,
    create_dividend,
):
    """ポートフォリオのテスト用データを作成するフィクスチャー

    日本株と米国株の取引および配当データを設定します。

    Args:
        setup_japanese_stock_data: 日本株のテストデータ
        setup_us_stock_data: 米国株のテストデータ
        create_dividend: 配当登録用フィクスチャー
    """
    # 日本株の配当データ
    japan_dividend = {
        "symbol": "8058",
        "payment_date": "2023-04-01T00:00:00Z",
        "shares_owned": "100.0",
        "total_amount": "1000.0",
        "tax": "200.0",
        "fee": "0.0",
    }
    await create_dividend(japan_dividend)

    # 米国株の配当データ
    us_dividend = {
        "symbol": "AAPL",
        "payment_date": "2023-03-15T00:00:00Z",
        "shares_owned": "10.0",
        "total_amount": "1500.0",
        "tax": "300.0",
        "fee": "0.0",
    }
    await create_dividend(us_dividend)


@pytest.mark.asyncio
async def test_get_portfolio_summary(client, auth_token, setup_portfolio_test_data):
    """ポートフォリオサマリー取得APIのテスト

    期待する動作:
    - ステータスコード200
    - 正しい合計値（取得価額、時価総額、含み損益など）
    - 市場別、通貨別集計が正しいこと

    Args:
        client: 非同期HTTPクライアント
        auth_token: 認証トークン
        setup_portfolio_test_data: テストデータ準備用フィクスチャー
    """
    # APIリクエスト実行
    response = await client.get("/api/v1/portfolio/summary", headers={"Authorization": f"Bearer {auth_token}"})

    # レスポンスの検証
    assert response.status_code == 200
    data = response.json()

    # 期待される合計値のチェック
    # 日本株: 100株 * 3000円 = 300,000円
    # 米国株: 10株 * 36054円 = 360,540円
    assert Decimal(str(data["total_cost"])) == Decimal("660540")

    assert data["total_market_value"] is not None
    assert data["total_unrealized_pl"] is not None
    assert Decimal(str(data["total_realized_pl"])) == Decimal("0")

    # 配当総額のチェック（税引後）
    # 日本株: 1000円 - 200円 = 800円
    # 米国株: 1500円 - 300円 = 1200円
    assert Decimal(str(data["total_dividend"])) == Decimal("2000")

    # 市場別集計のチェック
    assert len(data["holdings_by_market"]) == 2
    assert data["holdings_by_market"]["JPX"] is not None
    assert data["holdings_by_market"]["NASDAQ"] is not None

    # 通貨別集計のチェック
    assert len(data["holdings_by_currency"]) == 2
    assert data["holdings_by_currency"]["JPY"] is not None
    assert data["holdings_by_currency"]["USD"] is not None


@pytest.mark.asyncio
async def test_portfolio_update_with_price_changes(
    client, auth_token, setup_japanese_stock_data, setup_us_stock_data, create_dividend
):
    """ポートフォリオ更新機能のテスト (POST /api/v1/portfolio/summary)

    トランザクションと配当を登録し、ホールディングを更新した後、
    POSTメソッドでポートフォリオサマリーAPIにアクセスして正しく記録されることを確認します。

    期待される動作:
    - POSTリクエストが成功すること（ステータス200）
    - 日本株: 3,100円 × 100株 = 310,000円
    - 米国株: 250.0 USD × 10株 × 150.0 JPY = 375,000円
    - 配当金額が正しく計上されていること
    """
    # 配当データを登録
    japan_dividend = {
        "symbol": "8058",
        "payment_date": "2024-01-01T00:00:00Z",
        "shares_owned": "100.0",
        "total_amount": "1000.0",
        "tax": "200.0",
        "fee": "0.0",
    }
    us_dividend = {
        "symbol": "AAPL",
        "payment_date": "2024-01-01T00:00:00Z",
        "shares_owned": "10.0",
        "total_amount": "1500.0",
        "tax": "300.0",
        "fee": "0.0",
    }
    await create_dividend(japan_dividend)
    await create_dividend(us_dividend)

    # ホールディングの更新
    await client.post("/api/v1/holdings/8058/recalculate", headers={"Authorization": f"Bearer {auth_token}"})
    await client.post("/api/v1/holdings/AAPL/recalculate", headers={"Authorization": f"Bearer {auth_token}"})

    # POST /api/v1/portfolio/summary を呼び出してポートフォリオ履歴を作成
    response = await client.post("/api/v1/portfolio/summary", headers={"Authorization": f"Bearer {auth_token}"})

    # レスポンスの検証
    assert response.status_code == 200
    created_summary = response.json()

    # 期待値の確認
    assert Decimal(str(created_summary["total_market_value"])) == Decimal("685000.00")  # 310,000 + 375,000
    assert Decimal(str(created_summary["total_cost"])) == Decimal("660540.00")  # 取得価額の合計
    assert Decimal(str(created_summary["total_unrealized_pl"])) == Decimal("24460.00")  # 685,000 - 660,540
    assert Decimal(str(created_summary["total_dividend"])) == Decimal("2000.00")  # (1000 - 200) + (1500 - 300)

    # 市場別保有額の確認
    assert "JPX" in created_summary["holdings_by_market"]
    assert "NASDAQ" in created_summary["holdings_by_market"]
    assert Decimal(str(created_summary["holdings_by_market"]["JPX"])) == Decimal("310000.00")
    assert Decimal(str(created_summary["holdings_by_market"]["NASDAQ"])) == Decimal("375000.00")

    # 通貨別保有額の確認
    assert "JPY" in created_summary["holdings_by_currency"]
    assert "USD" in created_summary["holdings_by_currency"]

    # データベースに正しく記録されたことを確認するために、GET でも確認
    get_response = await client.get("/api/v1/portfolio/summary", headers={"Authorization": f"Bearer {auth_token}"})
    get_summary = get_response.json()

    # POSTとGETの結果が一致することを確認
    assert get_summary["total_market_value"] == created_summary["total_market_value"]
    assert get_summary["total_cost"] == created_summary["total_cost"]
    assert get_summary["total_dividend"] == created_summary["total_dividend"]
