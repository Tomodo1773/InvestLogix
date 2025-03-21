from decimal import Decimal
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from pytest_postgresql import factories
from pytest_postgresql.janitor import DatabaseJanitor
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from stock.app import app
from stock.database import get_db
from stock.models import Base
from stock.schemas import UserCreate
from stock.services.auth_service import AuthService

# pytest-asyncioのデフォルトスコープを設定
pytest_asyncio.fixture_default_loop_fixture_scope = "function"

# pytest-postgresqlのデフォルトスコープを設定
factories.postgresql.DEFAULT_FIXTURE_SCOPE = "function"
factories.postgresql_proc.DEFAULT_FIXTURE_SCOPE = "function"

# テスト用のDBのURL設定
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/test_investlogix"

# テスト用のエンジン設定
engine = create_async_engine(TEST_DATABASE_URL, echo=True, pool_size=5, max_overflow=10)

# テスト用のセッションファクトリ
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# テスト用の一時的なPostgreSQLインスタンスを設定
test_db = factories.postgresql_proc(host="localhost", port=5433, password="postgres")
test_postgres = factories.postgresql("test_db")


@pytest_asyncio.fixture(autouse=True, scope="function")
async def setup_database(test_postgres):
    """各テストで使用するデータベースの初期化を行うフィクスチャー

    各テスト実行前にデータベースを作成し、テスト終了後にクリーンアップを行います。

    Args:
        test_postgres: PostgreSQLのフィクスチャー

    Yields:
        SQLAlchemy AsyncEngine: テスト用の非同期エンジンインスタンス
    """
    db_params = test_postgres.info
    db_name = "test_investlogix"

    janitor = DatabaseJanitor(
        user=db_params.user,
        host=db_params.host,
        port=db_params.port,
        password="postgres",
        dbname=db_name,
        version=14,
    )

    try:
        janitor.init()

        # 非同期エンジンの設定
        db_url = f"postgresql+asyncpg://{db_params.user}:postgres@{db_params.host}:{db_params.port}/{db_name}"
        test_engine = create_async_engine(db_url, echo=True, pool_size=5, max_overflow=10)

        # テーブルの作成（テストケースごとに実行）
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield test_engine

        # テスト終了時のクリーンアップ
        await test_engine.dispose()
    finally:
        janitor.drop()


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
    user_data = {"username": "testuser", "email": "test@example.com", "password": "testpassword"}

    # db_sessionフィクスチャと独立したセッションでユーザー作成とコミットを実施
    async with TestingSessionLocalFunc() as session:
        await AuthService(session).create_user(UserCreate(**user_data))
        await session.commit()

    # ログインして認証トークンを取得
    response = await client.post("/api/v1/token", data={"username": user_data["username"], "password": user_data["password"]})
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
        TestingSessionLocalFunction = sessionmaker(setup_database, class_=AsyncSession, expire_on_commit=False)
        async with TestingSessionLocalFunction() as session:
            yield session

    # get_db依存性をオーバーライド
    app.dependency_overrides[get_db] = override_get_db
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
            TestingSessionLocalFunction = sessionmaker(setup_database, class_=AsyncSession, expire_on_commit=False)
            async with TestingSessionLocalFunction() as session:
                yield session

        return _override_get_db()

    app.dependency_overrides[get_db] = override_get_db
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
MOCK_JAPAN_STOCK_PRICE_INITIAL = Decimal("3000.0")  # 日本株価格（初期）
MOCK_US_STOCK_PRICE_INITIAL = Decimal("240.0")  # 米国株価格（USD）（初期）

# 株価モックデータ（更新後価格）
MOCK_JAPAN_STOCK_PRICE_UPDATED = Decimal("3100.0")  # 日本株価格（更新後）
MOCK_US_STOCK_PRICE_UPDATED = Decimal("250.0")  # 米国株価格（USD）（更新後）

MOCK_USD_JPY_RATE_RESPONSE = Decimal("150.0")  # 1 USD = 150.0 JPY

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

# JQuantsのレスポンスをモック化
MOCK_JQUANTS_COMPANY_INFO = {
    "CompanyName": "三菱商事",
    "CompanyNameEnglish": "Mitsubishi Corporation",
    "Sector17Code": "6050",
    "Sector17CodeName": "商社・卸売",
    "Sector33Code": "6050",
    "Sector33CodeName": "商社・卸売業",
    "MarketCodeName": "プライム",
    "ScaleCategory": "PRIME",
    "MarginCode": "1",
}


@pytest_asyncio.fixture(autouse=True)
async def mock_external_apis(mocker):
    """外部APIの応答をモック化するフィクスチャー

    以下の外部APIをモック化します：
    - AlphaVantage API（為替レート取得）
    - holdings_service（日本株・米国株の株価取得関数）

    Note:
        株価取得関数は呼び出し順序によって異なる値を返します：
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

    return {
        "overview": mock_overview,
        "search": mock_search,
        "japan_price": mock_japan_price,
        "us_price": mock_us_price,
        "usdjpy": mock_usdjpy,
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
