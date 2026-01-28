from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from stock.models import Holding
from ..conftest import MOCK_JAPAN_STOCK_PRICE_UPDATED, MOCK_US_STOCK_PRICE_UPDATED, MOCK_USD_JPY_RATE_RESPONSE


@pytest.mark.asyncio
async def test_recalculate_holding_pl_japanese_stock(
    client: AsyncClient, db_session: AsyncSession, auth_token: str, setup_japanese_stock_data
):
    """日本株の保有損益再計算テスト

    期待する動作:
    - ステータスコード200
    - 更新された保有情報を返却

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        setup_japanese_stock_data: 日本株のテストデータ
    """
    # 保有損益再計算APIを呼び出し
    response = await client.post(
        "/api/v1/holdings/8058/recalculate", headers={"Authorization": f"Bearer {auth_token}"}
    )

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "8058"
    assert Decimal(data["quantity"]) == Decimal("100.0")
    assert data["market_value"] is not None
    assert data["unrealized_pl"] is not None
    assert data["unrealized_pl_percentage"] is not None


@pytest.mark.asyncio
async def test_recalculate_holding_pl_us_stock(
    client: AsyncClient, db_session: AsyncSession, auth_token: str, setup_us_stock_data, mock_external_apis
):
    """米国株の保有損益再計算テスト

    期待する動作:
    - ステータスコード200
    - 更新された保有情報を返却
    - AlphaVantage APIのモックが呼び出されること

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        setup_us_stock_data: 米国株のテストデータ
        mock_external_apis: モック化されたAPI
    """
    # 保有損益再計算APIを呼び出し
    response = await client.post(
        "/api/v1/holdings/AAPL/recalculate", headers={"Authorization": f"Bearer {auth_token}"}
    )

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert Decimal(data["quantity"]) == Decimal("10.0")
    assert data["market_value"] is not None
    assert data["unrealized_pl"] is not None
    assert data["unrealized_pl_percentage"] is not None

    # トランザクション登録時の1回のAPI呼び出しを確認
    mock_external_apis["overview"].assert_called_once_with("AAPL")


@pytest.mark.asyncio
async def test_list_holdings(
    client: AsyncClient, db_session: AsyncSession, auth_token: str, setup_japanese_stock_data
):
    """保有銘柄一覧取得を確認するテスト

    期待する動作:
    - ステータスコード200
    - 保有銘柄情報に銘柄名、証券種別、通貨が含まれている

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        setup_japanese_stock_data: 日本株のテストデータ
    """
    # 保有銘柄一覧を取得
    response = await client.get("/api/v1/holdings/", headers={"Authorization": f"Bearer {auth_token}"})

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["stock_name"] == "三菱商事"
    assert data[0]["security_type"] == "STOCK"
    assert data[0]["currency"] == "JPY"


@pytest.mark.asyncio
async def test_recalculate_all_holdings_pl(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_token: str,
    setup_japanese_stock_data,
    setup_us_stock_data,
):
    """全銘柄の保有損益一括再計算のテスト

    期待する動作:
    - ステータスコード200
    - 日本株・米国株それぞれの更新された保有情報を返却
    - 各銘柄の最新株価が、初期価格から更新後価格に変更されていることを確認

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        setup_japanese_stock_data: 日本株のテストデータ
        setup_us_stock_data: 米国株のテストデータ
    """
    # 全銘柄の損益再計算APIを呼び出し
    response = await client.post(
        "/api/v1/holdings/recalculate-all", headers={"Authorization": f"Bearer {auth_token}"}
    )

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2  # 2銘柄分のデータがあることを確認

    # 各銘柄の更新を確認
    holdings = {h["symbol"]: h for h in data}

    # 日本株（8058）の検証
    assert "8058" in holdings
    jp_holding = holdings["8058"]
    assert (
        Decimal(jp_holding["current_price"]) == MOCK_JAPAN_STOCK_PRICE_UPDATED
    )  # 更新後の価格であることを確認
    assert Decimal(jp_holding["market_value"]) == MOCK_JAPAN_STOCK_PRICE_UPDATED * Decimal("100.0")
    assert jp_holding["unrealized_pl"] is not None
    assert jp_holding["unrealized_pl_percentage"] is not None

    # 米国株（AAPL）の検証
    assert "AAPL" in holdings
    us_holding = holdings["AAPL"]
    assert (
        Decimal(us_holding["current_price"]) == MOCK_US_STOCK_PRICE_UPDATED * MOCK_USD_JPY_RATE_RESPONSE
    )  # 更新後の価格であることを確認
    assert Decimal(
        us_holding["market_value"]
    ) == MOCK_US_STOCK_PRICE_UPDATED * MOCK_USD_JPY_RATE_RESPONSE * Decimal("10.0")
    assert us_holding["unrealized_pl"] is not None
    assert us_holding["unrealized_pl_percentage"] is not None


@pytest.mark.asyncio
async def test_recalculate_holding_pl_updates_realized_pl(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_token: str,
    create_transaction,
):
    """再計算APIがホールディングの実現損益を更新することを検証する"""

    # 取引を登録（10株購入後に5株売却）
    await create_transaction(
        {
            "symbol": "8058",
            "transaction_type": "buy",
            "quantity": "10.0",
            "price": "3000.0",
            "account_type": "NISA(成長投資枠)",
            "fee": "0.0",
            "tax": "0.0",
            "transaction_date": "2024-01-01T00:00:00",
        }
    )
    await create_transaction(
        {
            "symbol": "8058",
            "transaction_type": "sell",
            "quantity": "5.0",
            "price": "3500.0",
            "account_type": "NISA(成長投資枠)",
            "fee": "0.0",
            "tax": "0.0",
            "transaction_date": "2024-02-01T00:00:00",
        }
    )

    # 既存ホールディングの実現損益を0にリセットして過去データを再現
    result = await db_session.execute(select(Holding).where(Holding.symbol == "8058"))
    holding = result.scalar_one()
    await db_session.execute(
        update(Holding)
        .where(Holding.user_id == holding.user_id, Holding.symbol == holding.symbol)
        .values(realized_pl=Decimal("0"))
    )
    await db_session.commit()

    # 再計算APIを呼び出し、実現損益が更新されることを確認
    response = await client.post(
        "/api/v1/holdings/8058/recalculate", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["realized_pl"]) == Decimal("2500.0")


@pytest.mark.asyncio
async def test_recalculate_holding_pl_delisted_stock(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_token: str,
    create_transaction,
    create_dividend,
    mocker,
):
    """上場廃止銘柄でも実現損益と配当を反映した評価損益が計算されることを検証する

    期待する動作:
    - 株価が取得できない（0）場合でも、unrealized_pl が null にならない
    - unrealized_pl = market_value(0) + realized_pl + total_dividend - total_cost が計算される
    - 売却益と配当が正しく反映される

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
        auth_token: 認証トークン
        create_transaction: 取引作成フィクスチャ
        create_dividend: 配当作成フィクスチャ
        mocker: モックフィクスチャ
    """
    # 株価取得関数を上場廃止状態（価格=0）にモック
    mocker.patch("stock.services.holding_service.get_japan_stock_price", return_value=Decimal("0"))

    # 取引を登録（10株購入、3000円/株）
    await create_transaction(
        {
            "symbol": "8058",
            "transaction_type": "buy",
            "quantity": "10.0",
            "price": "3000.0",
            "account_type": "NISA(成長投資枠)",
            "fee": "0.0",
            "tax": "0.0",
            "transaction_date": "2024-01-01T00:00:00",
        }
    )

    # 5株売却（3500円/株、実現損益=+2500円）
    await create_transaction(
        {
            "symbol": "8058",
            "transaction_type": "sell",
            "quantity": "5.0",
            "price": "3500.0",
            "account_type": "NISA(成長投資枠)",
            "fee": "0.0",
            "tax": "0.0",
            "transaction_date": "2024-02-01T00:00:00",
        }
    )

    # 配当受取（1000円）
    await create_dividend(
        {
            "symbol": "8058",
            "payment_date": "2024-03-01T00:00:00",
            "shares_owned": "5.0",
            "total_amount": "1000.0",
            "tax": "200.0",
            "fee": "0.0",
        }
    )

    # 株価取得が0を返す状態で保有損益を再計算
    response = await client.post(
        "/api/v1/holdings/8058/recalculate", headers={"Authorization": f"Bearer {auth_token}"}
    )

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()

    # 保有数量: 5株
    assert Decimal(data["quantity"]) == Decimal("5.0")

    # 現在価格: 0（上場廃止）
    assert Decimal(data["current_price"]) == Decimal("0")

    # 時価評価額: 0
    assert Decimal(data["market_value"]) == Decimal("0")

    # 実現損益: +2500円
    assert Decimal(data["realized_pl"]) == Decimal("2500.0")

    # 配当総額: 800円（1000 - 200 税）
    assert Decimal(data["total_dividend"]) == Decimal("800.0")

    # 取得価格合計: 5株 × 3000円 = 15000円
    assert Decimal(data["total_cost"]) == Decimal("15000.0")

    # unrealized_pl（含み損益）= market_value(0) - total_cost(15000) = -15000
    assert data["unrealized_pl"] is not None
    expected_unrealized_pl = Decimal("0") - Decimal("15000")
    assert Decimal(data["unrealized_pl"]) == expected_unrealized_pl

    # total_pl = unrealized_pl(-15000) + realized_pl(2500) + total_dividend(800) = -11700
    assert data["total_pl"] is not None
    expected_total_pl = Decimal("-15000") + Decimal("2500") + Decimal("800")
    assert Decimal(data["total_pl"]) == expected_total_pl
