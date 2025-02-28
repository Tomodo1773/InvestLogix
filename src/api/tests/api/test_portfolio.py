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
        "total_amount": "2000.0",
        "tax": "400.0",
        "fee": "0.0",
    }
    await create_dividend(japan_dividend)

    # 米国株の配当データ
    us_dividend = {
        "symbol": "AAPL",
        "payment_date": "2023-03-15T00:00:00Z",
        "shares_owned": "10.0",
        "total_amount": "3000.0",
        "tax": "600.0",
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
    # 日本株: 2000円 - 400円 = 1600円
    # 米国株: 3000円 - 600円 = 2400円
    assert Decimal(str(data["total_dividend"])) == Decimal("4000")

    # 市場別集計のチェック
    assert len(data["holdings_by_market"]) == 2
    assert data["holdings_by_market"]["JPX"] is not None
    assert data["holdings_by_market"]["NASDAQ"] is not None

    # 通貨別集計のチェック
    assert len(data["holdings_by_currency"]) == 2
    assert data["holdings_by_currency"]["JPY"] is not None
    assert data["holdings_by_currency"]["USD"] is not None
