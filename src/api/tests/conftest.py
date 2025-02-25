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

# テスト用のDBのURL設定
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_investlogix"

# テスト用のエンジン設定
engine = create_async_engine(TEST_DATABASE_URL, echo=True, pool_size=5, max_overflow=10)

# テスト用のセッションファクトリ
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# テスト用の一時的なPostgreSQLインスタンスを設定
test_db = factories.postgresql_proc(port=None)
test_postgres = factories.postgresql("test_db")


@pytest_asyncio.fixture(autouse=True)
async def setup_database(test_postgres):
    """データベースの初期化を行うフィクスチャー"""
    db_params = test_postgres.info
    db_name = "test_investlogix"

    janitor = DatabaseJanitor(
        user=db_params.user,
        host=db_params.host,
        port=db_params.port,
        dbname=db_name,
        version=14,  # PostgreSQLのバージョンを指定
    )

    try:
        janitor.init()

        # 非同期エンジンの設定
        db_url = f"postgresql+asyncpg://{db_params.user}@{db_params.host}:{db_params.port}/{db_name}"
        test_engine = create_async_engine(db_url, echo=True, pool_size=5, max_overflow=10)

        # テーブルの作成
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        yield test_engine

        # テスト終了後のクリーンアップ
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await test_engine.dispose()
    finally:
        janitor.drop()


@pytest_asyncio.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """非同期データベースセッションのフィクスチャー"""
    TestingSessionLocal = sessionmaker(setup_database, class_=AsyncSession, expire_on_commit=False)
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture
async def auth_token(client: AsyncClient, db_session: AsyncSession) -> str:
    """テスト用の認証トークンを取得するフィクスチャー"""
    # テストユーザーを作成
    user_data = {"username": "testuser", "email": "test@example.com", "password": "testpassword"}
    await AuthService(db_session).create_user(UserCreate(**user_data))

    # ログインしてトークンを取得
    response = await client.post("/api/v1/token", data={"username": user_data["username"], "password": user_data["password"]})
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """非同期HTTPクライアントのフィクスチャー"""

    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def sync_client() -> Generator[TestClient, None, None]:
    """同期HTTPクライアントのフィクスチャー"""

    def override_get_db():
        async def _override_get_db():
            async with TestingSessionLocal() as session:
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

MOCK_ETF_SEARCH_RESPONSE = {
    "bestMatches": [
        {
            "1. symbol": "SPYD",
            "2. name": "SPDR(R) PORTFOLIO S&P 500 HIGH DIVIDEND ETF",  # 末尾のスペースを削除
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

MOCK_USD_JPY_RATE_RESPONSE = 150.0

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


@pytest_asyncio.fixture
async def mocker(request):
    """async版のmockerフィクスチャー"""
    return request.getfixturevalue("mocker")


@pytest_asyncio.fixture(autouse=True)
async def mock_external_apis(mocker):
    """外部APIの応答をモック化するフィクスチャー"""
    # AlphaVantage APIのモック（stock_service内で使用されるのでパスを変更）
    mock_overview = mocker.patch("stock.services.stock_service.fetch_us_stock_overview", autospec=True)
    mock_overview.return_value = MOCK_STOCK_OVERVIEW_RESPONSE

    mock_search = mocker.patch("stock.services.stock_service.fetch_us_stock_search", autospec=True)
    mock_search.return_value = MOCK_ETF_SEARCH_RESPONSE

    return {
        "overview": mock_overview,
        "search": mock_search,
    }
