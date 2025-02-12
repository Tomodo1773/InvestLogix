from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from stock.app import app
from stock.database import get_db, settings
from stock.schemas import UserCreate
from stock.services.auth_service import AuthService

# テスト用のエンジン設定をアプリケーションの設定から取得
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# テスト用のセッションファクトリ
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """非同期データベースセッションのフィクスチャー"""
    async with TestingSessionLocal() as session:
        yield session
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
