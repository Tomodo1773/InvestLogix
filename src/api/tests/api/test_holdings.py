import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from stock.models import Holding, User
from stock.services.holding_service import update_all_holdings_pl
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
    response = await client.post("/api/v1/holdings/8058/recalculate")

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "8058"
    assert float(data["quantity"]) == 100.0
    assert data["market_value"] is not None
    assert data["unrealized_pl"] is not None
    assert data["unrealized_pl_percentage"] is not None
    assert data["total_pl"] is not None
    assert data["total_pl_percentage"] is not None


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
    response = await client.post("/api/v1/holdings/AAPL/recalculate")

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert float(data["quantity"]) == 10.0
    assert data["market_value"] is not None
    assert data["unrealized_pl"] is not None
    assert data["unrealized_pl_percentage"] is not None
    assert data["total_pl"] is not None
    assert data["total_pl_percentage"] is not None

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
    response = await client.get("/api/v1/holdings/")

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["stock_name"] == "三菱商事"
    assert data[0]["security_type"] == "STOCK"
    assert data[0]["currency"] == "JPY"
    # JPY建ての日本株は country=="JP"、JQuants から取得した 17 業種名が sector_name に入る
    assert data[0]["country"] == "JP"
    assert data[0]["sector_name"] == "商社・卸売"


@pytest.mark.asyncio
async def test_list_holdings_returns_country_and_sector_for_us(
    client: AsyncClient, db_session: AsyncSession, auth_token: str, setup_us_stock_data
):
    """USD建ての米国株は country=="US"、AlphaVantage から取得した gics_sector が sector_name に入る"""
    response = await client.get("/api/v1/holdings/")

    assert response.status_code == 200
    data = response.json()
    target = next(h for h in data if h["symbol"] == "AAPL")
    assert target["country"] == "US"
    assert target["sector_name"] == "Technology"


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
    response = await client.post("/api/v1/holdings/recalculate-all")

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2  # 2銘柄分のデータがあることを確認

    # 各銘柄の更新を確認
    holdings = {h["symbol"]: h for h in data}

    # 日本株（8058）の検証
    assert "8058" in holdings
    jp_holding = holdings["8058"]
    assert float(jp_holding["current_price"]) == float(
        MOCK_JAPAN_STOCK_PRICE_UPDATED
    )  # 更新後の価格であることを確認
    assert float(jp_holding["market_value"]) == float(MOCK_JAPAN_STOCK_PRICE_UPDATED) * 100.0
    assert jp_holding["unrealized_pl"] is not None
    assert jp_holding["unrealized_pl_percentage"] is not None

    # 米国株（AAPL）の検証
    assert "AAPL" in holdings
    us_holding = holdings["AAPL"]
    assert float(us_holding["current_price"]) == float(MOCK_US_STOCK_PRICE_UPDATED) * float(
        MOCK_USD_JPY_RATE_RESPONSE
    )  # 更新後の価格であることを確認
    assert (
        float(us_holding["market_value"])
        == float(MOCK_US_STOCK_PRICE_UPDATED) * float(MOCK_USD_JPY_RATE_RESPONSE) * 10.0
    )
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
        .values(realized_pl=0.0)
    )
    await db_session.commit()

    # 再計算APIを呼び出し、実現損益が更新されることを確認
    response = await client.post("/api/v1/holdings/8058/recalculate")
    assert response.status_code == 200
    data = response.json()
    assert float(data["realized_pl"]) == 2500.0


@pytest.mark.asyncio
async def test_recalculate_holding_pl_delisted_stock(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_token: str,
    create_transaction,
    create_dividend,
    mocker,
):
    """上場廃止銘柄でも含み損益と全体損益が正しく計算されることを検証する

    期待する動作:
    - 株価が取得できない（0）場合でも、unrealized_pl と total_pl が null にならない
    - unrealized_pl = market_value(0) - total_cost が計算される（純粋な含み益）
    - total_pl = unrealized_pl + realized_pl + total_dividend が計算される（全体損益）
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
    mocker.patch("stock.services.holding_service.get_japan_stock_price", return_value=0.0)

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
    response = await client.post("/api/v1/holdings/8058/recalculate")

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()

    # 保有数量: 5株
    assert float(data["quantity"]) == 5.0

    # 現在価格: 0（上場廃止）
    assert float(data["current_price"]) == 0.0

    # 時価評価額: 0
    assert float(data["market_value"]) == 0.0

    # 実現損益: +2500円
    assert float(data["realized_pl"]) == 2500.0

    # 配当総額: 800円（1000 - 200 税）
    assert float(data["total_dividend"]) == 800.0

    # 取得価格合計: 5株 × 3000円 = 15000円
    assert float(data["total_cost"]) == 15000.0

    # unrealized_pl が null ではなく計算されていることを確認
    assert data["unrealized_pl"] is not None

    # unrealized_pl = market_value(0) - total_cost(15000)
    #                = 0 - 15000
    #                = -15000
    expected_unrealized_pl = 0.0 - 15000.0
    assert float(data["unrealized_pl"]) == expected_unrealized_pl

    # total_pl が null ではなく計算されていることを確認
    assert data["total_pl"] is not None

    # total_pl = unrealized_pl(-15000) + realized_pl(2500) + total_dividend(800)
    #          = -15000 + 2500 + 800
    #          = -11700
    expected_total_pl = -15000.0 + 2500.0 + 800.0
    assert float(data["total_pl"]) == expected_total_pl


@pytest.mark.asyncio
async def test_update_holding_note(
    client: AsyncClient, db_session: AsyncSession, auth_token: str, setup_japanese_stock_data
):
    """保有銘柄のメモ更新テスト

    期待する動作:
    - ステータスコード200
    - レスポンスにメモが含まれる
    - 一覧取得APIでもメモが取得できる
    """
    # メモを更新
    response = await client.put(
        "/api/v1/holdings/8058/note",
        json={"note": "総合商社。資源価格と配当に期待。"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "8058"
    assert data["note"] == "総合商社。資源価格と配当に期待。"
    assert data["stock_name"] == "三菱商事"

    # 一覧取得でもメモが取得できる
    list_response = await client.get("/api/v1/holdings/?symbol=8058")
    assert list_response.status_code == 200
    assert list_response.json()[0]["note"] == "総合商社。資源価格と配当に期待。"


@pytest.mark.asyncio
async def test_update_holding_note_clear(
    client: AsyncClient, db_session: AsyncSession, auth_token: str, setup_japanese_stock_data
):
    """メモにnullを送るとクリアできることを検証する"""
    # 一旦書き込み
    await client.put(
        "/api/v1/holdings/8058/note",
        json={"note": "あとで消す"},
    )

    # nullで上書き
    response = await client.put(
        "/api/v1/holdings/8058/note",
        json={"note": None},
    )

    assert response.status_code == 200
    assert response.json()["note"] is None


@pytest.mark.asyncio
async def test_update_holding_note_not_found(client: AsyncClient, auth_token: str):
    """未保有銘柄に対するメモ更新は404"""
    response = await client.put(
        "/api/v1/holdings/UNKNOWN/note",
        json={"note": "test"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_all_holdings_pl_returns_failed_symbols(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_token: str,
    setup_japanese_stock_data,
    setup_us_stock_data,
    mocker,
):
    """update_all_holdings_pl が価格取得失敗銘柄リストを第2要素として返すことを検証する。

    米国株(AAPL)の価格取得を 0.0（取得失敗）に固定し、戻り値の失敗リストに含まれることを確認する。
    日本株(8058)はデフォルトのモックで取得成功するため失敗リストに含まれない。
    """
    # 米国株の価格取得を失敗させる
    mocker.patch("stock.services.holding_service.get_us_stock_price", return_value=0.0)

    # auth_token フィクスチャで作成済みのテストユーザ ID を取得
    result = await db_session.execute(select(User).where(User.username == "testuser"))
    user_id = result.scalar_one().user_id

    holdings, failed_symbols = await update_all_holdings_pl(db_session, user_id)

    assert "AAPL" in failed_symbols
    assert "8058" not in failed_symbols
    # 日本株は更新成功している
    assert any(h.symbol == "8058" for h in holdings)


@pytest.mark.asyncio
async def test_update_all_holdings_pl_skips_zero_quantity(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_token: str,
    setup_us_stock_data,
    create_transaction,
    mocker,
):
    """保有数ゼロの銘柄は価格取得自体をスキップし、失敗リストに含めないことを検証する。

    AAPL を全量売却して quantity=0 にしたうえで、価格取得を 0.0（失敗）に固定しても
    failed_symbols に AAPL が含まれないことを確認する。売却済み・上場廃止銘柄で
    アラートが誤発火しないための回帰テスト。価格 / usd_price は損益計算結果に影響しないので
    任意の妥当値を入れている。
    """
    sell_transaction = {
        "symbol": "AAPL",
        "transaction_type": "sell",
        "quantity": "10.0",
        "price": "37500",
        "usd_price": "250.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-02-01T00:00:00",
    }
    await create_transaction(sell_transaction)

    mocker.patch("stock.services.holding_service.get_us_stock_price", return_value=0.0)

    result = await db_session.execute(select(User).where(User.username == "testuser"))
    user_id = result.scalar_one().user_id

    _, failed_symbols = await update_all_holdings_pl(db_session, user_id)

    assert "AAPL" not in failed_symbols
