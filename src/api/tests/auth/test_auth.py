"""認証済みユーザーの解決とユーザー管理APIのテスト"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from stock.app import app
from stock.auth import get_access_identity
from stock.cloudflare_access import AccessIdentity
from stock.schemas import UserBase
from stock.services.user_service import UserService
from tests.conftest import TEST_ACCESS_ISSUER


def _authenticate_as(identity: AccessIdentity) -> None:
    """Access JWTの検証結果を差し替える（検証自体は test_access_token.py で確認済み）"""
    app.dependency_overrides[get_access_identity] = lambda: identity


@pytest.mark.asyncio
async def test_me_returns_current_user(client: AsyncClient, auth_user: AccessIdentity):
    """認証済みユーザーの情報を返すこと"""
    response = await client.get("/api/v1/users/me")

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == auth_user.email


@pytest.mark.asyncio
async def test_request_without_access_jwt_is_rejected(client: AsyncClient):
    """Access JWTが無いリクエストを拒否すること（Cloud Runへの直アクセス対策）"""
    response = await client.get("/api/v1/users/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_unregistered_access_user_is_rejected(client: AsyncClient):
    """Access認証は通ってもアプリに未登録の利用者を拒否すること"""
    _authenticate_as(
        AccessIdentity(issuer=TEST_ACCESS_ISSUER, subject="unknown-sub", email="stranger@example.com")
    )

    response = await client.get("/api/v1/users/me")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_first_login_links_access_identity(client: AsyncClient, db_session: AsyncSession):
    """初回ログインでAccessの外部IDが紐付き、以降はメールアドレスに依存せず解決されること"""
    await UserService(db_session).create_user(UserBase(username="newcomer", email="newcomer@example.com"))
    await db_session.commit()

    # 初回はAccessが確認済みのメールアドレスで紐付く
    _authenticate_as(
        AccessIdentity(issuer=TEST_ACCESS_ISSUER, subject="newcomer-sub", email="newcomer@example.com")
    )
    first = await client.get("/api/v1/users/me")

    assert first.status_code == 200
    assert first.json()["username"] == "newcomer"

    # IdP側でメールアドレスが変わっても、紐付いた subject で同じユーザーへ解決される
    _authenticate_as(
        AccessIdentity(issuer=TEST_ACCESS_ISSUER, subject="newcomer-sub", email="renamed@example.com")
    )
    second = await client.get("/api/v1/users/me")

    assert second.status_code == 200
    assert second.json()["user_id"] == first.json()["user_id"]


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient, auth_admin_user: AccessIdentity):
    """管理者が新規ユーザーを登録できること"""
    user_data = {"username": "testuser2", "email": "test2@example.com"}

    response = await client.post("/api/v1/users/", json=user_data)

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]


@pytest.mark.asyncio
async def test_create_duplicate_user(client: AsyncClient, auth_admin_user: AccessIdentity):
    """重複するユーザー名/メールアドレスの登録を拒否すること"""
    user_data = {"username": "testuser3", "email": "test3@example.com"}

    await client.post("/api/v1/users/", json=user_data)
    response = await client.post("/api/v1/users/", json=user_data)

    assert response.status_code == 400
    assert response.json()["detail"] == "Username or email already registered"


@pytest.mark.asyncio
async def test_create_user_without_admin_privileges(client: AsyncClient, auth_user: AccessIdentity):
    """管理者権限のないユーザーからのユーザー登録を拒否すること"""
    user_data = {"username": "newuser", "email": "newuser@example.com"}

    response = await client.post("/api/v1/users/", json=user_data)

    assert response.status_code == 403
    assert response.json()["detail"] == "管理者権限が必要です"
