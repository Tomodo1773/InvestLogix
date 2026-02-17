import asyncio
import uuid
from typing import AsyncGenerator, Generator

import psycopg
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from stock.app import app
from stock.auth import get_db_for_user
from stock.database import get_db
from stock.models import Base
from stock.schemas import UserCreate
from stock.services.auth_service import AuthService

# pytest-asyncioのデフォルトスコープを設定
pytest_asyncio.fixture_default_loop_fixture_scope = "function"


def _render_url(url: URL) -> str:
    return url.render_as_string(hide_password=False)


def _admin_connection_url(base_connection_url: str) -> str:
    url = make_url(base_connection_url)
    url = url.set(database="postgres")
    # psycopg3はドライバ指定子を含まない形式を要求するため、postgresql://に変更
    url = url.set(drivername="postgresql")
    return _render_url(url)


def _async_db_url(base_connection_url: str, database: str) -> str:
    url = make_url(base_connection_url)
    url = url.set(drivername="postgresql+asyncpg")
    url = url.set(database=database)
    return _render_url(url)


@pytest.fixture(scope="session")
def base_connection_url() -> Generator[str, None, None]:
    container = PostgresContainer("postgres:16-alpine")
    container.start()
    try:
        yield container.get_connection_url()
    finally:
        container.stop()


@pytest_asyncio.fixture(scope="session", autouse=True, loop_scope="session")
async def bootstrap_schema(base_connection_url: str) -> AsyncGenerator[str, None]:
    template_db_name = "template_investlogix"
    admin_url = _admin_connection_url(base_connection_url)

    def _prepare_template_database() -> None:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (template_db_name,))
                exists = cur.fetchone()
            if not exists:
                conn.execute(f'CREATE DATABASE "{template_db_name}"')

    await asyncio.to_thread(_prepare_template_database)

    template_async_url = _async_db_url(base_connection_url, template_db_name)
    # poolclass=NullPoolでコネクションプールを無効化し、engine.dispose()で確実に接続を閉じる
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(template_async_url, echo=True, poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        # テンプレート作成後、即座にengineを破棄して接続を確実に閉じる
        await engine.dispose()
        yield template_db_name
    finally:

        def _drop_template_database() -> None:
            with psycopg.connect(admin_url, autocommit=True) as conn:
                conn.execute(f'DROP DATABASE IF EXISTS "{template_db_name}" WITH (FORCE)')

        await asyncio.to_thread(_drop_template_database)


@pytest.fixture(scope="function")
def db_url(base_connection_url: str, bootstrap_schema: str) -> Generator[str, None, None]:
    template_db_name = bootstrap_schema
    admin_url = _admin_connection_url(base_connection_url)
    db_name = f"t_{uuid.uuid4().hex[:8]}"

    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(f'CREATE DATABASE "{db_name}" TEMPLATE "{template_db_name}"')

    database_url = _async_db_url(base_connection_url, db_name)
    try:
        yield database_url
    finally:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            conn.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)')


@pytest_asyncio.fixture(autouse=True, scope="function")
async def setup_database(db_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """各テストで使用するデータベースの初期化を行うフィクスチャー

    各テスト実行前にデータベースを作成し、テスト終了後にクリーンアップを行います。

    Args:
        db_url: テスト用のデータベースURL

    Yields:
        SQLAlchemy AsyncEngine: テスト用の非同期エンジンインスタンス
    """
    test_engine = create_async_engine(db_url, echo=True, pool_size=5, max_overflow=10)

    try:
        yield test_engine
    finally:
        await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """非同期データベースセッションのフィクスチャー

    各テストは独立したトランザクション内で実行され、テスト終了後に自動的にロールバックされます。

    Args:
        setup_database: データベースセットアップのフィクスチャー

    Yields:
        AsyncSession: テスト用の非同期セッションインスタンス
    """
    TestingSessionLocal = sessionmaker(setup_database, class_=AsyncSession, expire_on_commit=False)

    async with TestingSessionLocal() as session:
        # トランザクションを開始
        async with session.begin():
            yield session
            # トランザクションは自動的にロールバックされます


@pytest_asyncio.fixture
async def auth_token(client: AsyncClient, setup_database) -> str:
    """テスト用の認証トークンを取得するフィクスチャー

    認証ユーザーを新規作成し、コミットすることで別セッションでも参照可能にします。

    Args:
        client: 非同期HTTPクライアント
        setup_database: データベースセットアップのフィクスチャー

    Returns:
        str: JWTアクセストークン
    """
    from sqlalchemy.orm import sessionmaker

    # setup_databaseから新しいセッションファクトリを作成
    TestingSessionLocalFunc = sessionmaker(setup_database, class_=AsyncSession, expire_on_commit=False)

    # テストユーザーのデータ
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword",
        "is_admin": False,
    }

    # db_sessionフィクスチャと独立したセッションでユーザー作成とコミットを実施
    async with TestingSessionLocalFunc() as session:
        await AuthService(session).create_user(UserCreate(**user_data))
        await session.commit()

    # ログインして認証トークンを取得（JSON形式でリクエスト）
    login_data = {"username": user_data["username"], "password": user_data["password"]}
    response = await client.post("/api/v1/token", json=login_data)
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def auth_admin_token(client: AsyncClient, setup_database) -> str:
    """テスト用の管理者権限トークンを取得するフィクスチャー

    管理者権限を持つユーザーを新規作成し、コミットすることで別セッションでも参照可能にします。

    Args:
        client: 非同期HTTPクライアント
        setup_database: データベースセットアップのフィクスチャー

    Returns:
        str: 管理者権限のJWTアクセストークン
    """
    from sqlalchemy.orm import sessionmaker

    # setup_databaseから新しいセッションファクトリを作成
    TestingSessionLocalFunc = sessionmaker(setup_database, class_=AsyncSession, expire_on_commit=False)

    # 管理者ユーザーのデータ
    admin_user_data = {"username": "adminuser", "email": "admin@example.com", "password": "adminpassword"}

    # db_sessionフィクスチャと独立したセッションでユーザー作成とコミットを実施
    async with TestingSessionLocalFunc() as session:
        # is_admin=Trueを明示的に渡す
        await AuthService(session).create_user(UserCreate(**admin_user_data), is_admin=True)
        await session.commit()

    # ログインして認証トークンを取得（JSON形式でリクエスト）
    login_data = {"username": admin_user_data["username"], "password": admin_user_data["password"]}
    response = await client.post("/api/v1/token", json=login_data)
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def client(setup_database) -> AsyncGenerator[AsyncClient, None]:
    """非同期HTTPクライアントのフィクスチャー

    テスト用のデータベース接続をオーバーライドした非同期HTTPクライアントを提供します。

    Args:
        setup_database: データベースセットアップのフィクスチャー

    Yields:
        AsyncClient: 非同期HTTPクライアントインスタンス
    """

    async def override_get_db():
        # setup_databaseから新しいセッションファクトリを作成
        TestingSessionLocalFunction = sessionmaker(
            setup_database, class_=AsyncSession, expire_on_commit=False
        )
        async with TestingSessionLocalFunction() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    # get_db / get_db_for_user 依存性をオーバーライド
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_for_user] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def sync_client(setup_database) -> Generator[TestClient, None, None]:
    """同期HTTPクライアントのフィクスチャー

    テスト用のデータベース接続をオーバーライドした同期HTTPクライアントを提供します。

    Args:
        setup_database: データベースセットアップのフィクスチャー

    Yields:
        TestClient: 同期HTTPクライアントインスタンス
    """

    def override_get_db():
        async def _override_get_db():
            # setup_databaseから新しいセッションファクトリを作成
            TestingSessionLocalFunction = sessionmaker(
                setup_database, class_=AsyncSession, expire_on_commit=False
            )
            async with TestingSessionLocalFunction() as session:
                yield session

        return _override_get_db()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_for_user] = override_get_db
    with TestClient(app=app) as client:
        yield client
    app.dependency_overrides.clear()


# モックレスポンスの定義
MOCK_STOCK_OVERVIEW_RESPONSE = {
    "Symbol": "AAPL",
    "Name": "Apple Inc",
    "Exchange": "NASDAQ",
    "Sector": "Technology",
    "Industry": "Consumer Electronics",
}

# 株価モックデータ（初期価格）
MOCK_JAPAN_STOCK_PRICE_INITIAL = 3000.0  # 日本株価格（初期）
MOCK_US_STOCK_PRICE_INITIAL = 240.0  # 米国株価格（USD）（初期）

# 株価モックデータ（更新後価格）
MOCK_JAPAN_STOCK_PRICE_UPDATED = 3100.0  # 日本株価格（更新後）
MOCK_US_STOCK_PRICE_UPDATED = 250.0  # 米国株価格（USD）（更新後）

MOCK_USD_JPY_RATE_RESPONSE = 150.0  # 1 USD = 150.0 JPY

MOCK_ETF_SEARCH_RESPONSE = {
    "bestMatches": [
        {
            "1. symbol": "SPYD",
            "2. name": "SPDR(R) PORTFOLIO S&P 500 HIGH DIVIDEND ETF",
            "3. type": "ETF",
            "4. region": "United States",
            "5. marketOpen": "09:30",
            "6. marketClose": "16:00",
            "7. timezone": "UTC-04",
            "8. currency": "USD",
            "9. matchScore": "1.0000",
        }
    ]
}

# JQuantsのレスポンスをモック化（V2形式）
MOCK_JQUANTS_COMPANY_INFO = {
    "CoName": "三菱商事",
    "CoNameEn": "Mitsubishi Corporation",
    "S17": "60",  # 17業種コード（2桁）
    "S17Nm": "商社・卸売",
    "S33": "6050",  # 33業種コード（4桁）
    "S33Nm": "商社・卸売業",
    "MktNm": "プライム",
    "ScaleCat": "PRIME",
    "MarginCode": "1",
}

# JQuantsの株価データモック（V2形式）
MOCK_JQUANTS_PRICE_DATA = [
    {
        "Date": "2024-01-01",
        "Code": "8058",
        "Open": 3000.0,
        "High": 3100.0,
        "Low": 2900.0,
        "Close": 3000.0,
        "Volume": 1000000,
    }
]


@pytest_asyncio.fixture(autouse=True)
async def mock_external_apis(mocker):
    """外部APIの応答をモック化するフィクスチャー

    以下の外部APIをモック化します:
    - AlphaVantage API（為替レート取得）
    - holdings_service（日本株・米国株の株価取得関数）
    - JQuants API（銘柄情報、株価取得）

    Note:
        株価取得関数は呼び出し順序によって異なる値を返します:
        - get_japan_stock_price:
            1回目: MOCK_JAPAN_STOCK_PRICE_INITIAL (3000.0)
            2回目以降: MOCK_JAPAN_STOCK_PRICE_UPDATED (3100.0)
        - get_us_stock_price:
            1回目: MOCK_US_STOCK_PRICE_INITIAL * MOCK_USD_JPY_RATE_RESPONSE (36000.0)
            2回目以降: MOCK_US_STOCK_PRICE_UPDATED * MOCK_USD_JPY_RATE_RESPONSE (37500.0)

    Args:
        mocker: モッカーフィクスチャー

    Returns:
        dict: モックオブジェクトを含む辞書
    """
    # AlphaVantage APIのモック（stock_service内で使用）
    mock_overview = mocker.patch("stock.services.stock_service.fetch_us_stock_overview", autospec=True)
    mock_overview.return_value = MOCK_STOCK_OVERVIEW_RESPONSE

    mock_search = mocker.patch("stock.services.stock_service.fetch_us_stock_search", autospec=True)
    mock_search.return_value = MOCK_ETF_SEARCH_RESPONSE

    # holdings_serviceの株価取得関数をモック化（初回と2回目以降で異なる値を返す）
    mock_japan_price = mocker.patch("stock.services.holding_service.get_japan_stock_price", autospec=True)
    mock_japan_price.side_effect = [MOCK_JAPAN_STOCK_PRICE_INITIAL] + [MOCK_JAPAN_STOCK_PRICE_UPDATED] * 10

    mock_us_price = mocker.patch("stock.services.holding_service.get_us_stock_price", autospec=True)
    mock_us_price.side_effect = [MOCK_US_STOCK_PRICE_INITIAL * MOCK_USD_JPY_RATE_RESPONSE] + [
        MOCK_US_STOCK_PRICE_UPDATED * MOCK_USD_JPY_RATE_RESPONSE
    ] * 10

    mock_usdjpy = mocker.patch("stock.services.alphavantage_service.fetch_usdjpy_rate", autospec=True)
    mock_usdjpy.return_value = MOCK_USD_JPY_RATE_RESPONSE

    # JQuantsクライアントのモック化
    mock_jquants_client = mocker.Mock()
    mock_jquants_client.get_company_info.return_value = MOCK_JQUANTS_COMPANY_INFO
    # get_pricesは非同期メソッドなので、AsyncMockを使用
    mock_jquants_client.get_prices = mocker.AsyncMock(return_value=MOCK_JQUANTS_PRICE_DATA)

    # 各サービスファイルでインポートされたget_jquants_clientをモック化
    mocker.patch("stock.services.stock_service.get_jquants_client", return_value=mock_jquants_client)
    mocker.patch("stock.services.stock_price_fetcher.get_jquants_client", return_value=mock_jquants_client)
    mocker.patch("stock.services.price_history_service.get_jquants_client", return_value=mock_jquants_client)

    return {
        "overview": mock_overview,
        "search": mock_search,
        "japan_price": mock_japan_price,
        "us_price": mock_us_price,
        "usdjpy": mock_usdjpy,
        "jquants_client": mock_jquants_client,
    }


@pytest_asyncio.fixture
async def mocker(request):
    """非同期テスト用のmockerフィクスチャー

    Args:
        request: リクエストコンテキスト

    Returns:
        pytest_mock.MockFixture: モッキングユーティリティ
    """
    return request.getfixturevalue("mocker")


@pytest_asyncio.fixture
async def create_transaction(client, auth_token):
    """取引データを登録するためのユーティリティフィクスチャー

    Args:
        client: 非同期HTTPクライアント
        auth_token: 認証トークン

    Returns:
        function: 取引登録用の関数
    """

    async def _create_transaction(transaction_data):
        response = await client.post(
            "/api/v1/transactions/", json=transaction_data, headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        return response.json()

    return _create_transaction


@pytest_asyncio.fixture
async def create_dividend(client, auth_token):
    """配当データを登録するためのユーティリティフィクスチャー

    Args:
        client: 非同期HTTPクライアント
        auth_token: 認証トークン

    Returns:
        function: 配当登録用の関数
    """

    async def _create_dividend(dividend_data):
        response = await client.post(
            "/api/v1/dividends/", json=dividend_data, headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        return response.json()

    return _create_dividend


@pytest_asyncio.fixture
async def setup_dividend_data(create_dividend):
    """配当データをセットアップするフィクスチャー

    Args:
        create_dividend: 配当登録フィクスチャー

    Returns:
        dict: 配当情報
    """
    # 日本株の配当データ
    dividend_data_jp = {
        "symbol": "8058",
        "payment_date": "2024-01-01T00:00:00",
        "shares_owned": "100.0",
        "total_amount": "2000.0",
        "tax": "400.0",
        "fee": "0.0",
    }
    jp_dividend = await create_dividend(dividend_data_jp)

    # 米国株の配当データ
    dividend_data_us = {
        "symbol": "AAPL",
        "payment_date": "2024-01-01T00:00:00",
        "shares_owned": "10.0",
        "total_amount": "3000.0",
        "tax": "600.0",
        "fee": "0.0",
    }
    us_dividend = await create_dividend(dividend_data_us)

    return {"jp_dividend": jp_dividend, "us_dividend": us_dividend}


@pytest_asyncio.fixture
async def setup_japanese_stock_data(client, auth_token, create_transaction):
    """日本株のテストデータをセットアップするフィクスチャー

    Args:
        client: 非同期HTTPクライアント
        create_transaction: 取引登録フィクスチャー
        auth_token: 認証トークン

    Returns:
        dict: 取引情報
    """
    # 取引データ登録
    transaction_data = {
        "symbol": "8058",
        "transaction_type": "buy",
        "quantity": "100.0",
        "price": "3000.0",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }
    return await create_transaction(transaction_data)


@pytest_asyncio.fixture
async def setup_us_stock_data(client, auth_token, create_transaction):
    """米国株のテストデータをセットアップするフィクスチャー

    Args:
        client: 非同期HTTPクライアント
        create_transaction: 取引登録フィクスチャー
        auth_token: 認証トークン

    Returns:
        dict: 取引情報
    """
    # 取引データ登録
    transaction_data = {
        "symbol": "AAPL",
        "transaction_type": "buy",
        "quantity": "10.0",
        "price": "36054",
        "usd_price": "240.36",
        "account_type": "NISA(成長投資枠)",
        "fee": "0.0",
        "tax": "0.0",
        "transaction_date": "2024-01-01T00:00:00",
    }
    return await create_transaction(transaction_data)


@pytest_asyncio.fixture
async def setup_portfolio_test_data(setup_japanese_stock_data, setup_us_stock_data, create_dividend):
    """ポートフォリオのテスト用データを作成するフィクスチャー

    基本データセットアップ後に配当データを登録します。

    Args:
        setup_japanese_stock_data: 日本株のテストデータ
        setup_us_stock_data: 米国株のテストデータ
        create_dividend: 配当登録用フィクスチャー
    """
    # 日本株の配当データ
    japan_dividend = {
        "symbol": "8058",
        "payment_date": "2024-01-01T00:00:00Z",
        "shares_owned": "100.0",
        "total_amount": "1000.0",
        "tax": "200.0",
        "fee": "0.0",
    }
    jp_dividend = await create_dividend(japan_dividend)

    # 米国株の配当データ
    us_dividend = {
        "symbol": "AAPL",
        "payment_date": "2024-01-01T00:00:00Z",
        "shares_owned": "10.0",
        "total_amount": "1500.0",
        "tax": "300.0",
        "fee": "0.0",
    }
    apple_dividend = await create_dividend(us_dividend)

    return {
        "japanese_stock": setup_japanese_stock_data,
        "us_stock": setup_us_stock_data,
        "dividends": {"jp": jp_dividend, "us": apple_dividend},
    }
