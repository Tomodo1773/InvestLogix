import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from stock.schemas import UserCreate
from stock.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient, db_session: AsyncSession):
    """新規ユーザー登録のテスト

    期待する動作:
    - ステータスコード200
    - 作成されたユーザー情報を返却
    - パスワードハッシュが含まれない

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
    """
    # テストデータ準備
    user_data = {"username": "testuser2", "email": "test2@example.com", "password": "testpassword"}

    # APIリクエスト実行
    response = await client.post("/api/v1/users/", json=user_data)

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_create_duplicate_user(client: AsyncClient, db_session: AsyncSession):
    """重複ユーザー登録のテスト

    期待する動作:
    - ステータスコード400
    - エラーメッセージを返却

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
    """
    # テストデータ準備
    user_data = {"username": "testuser", "email": "test@example.com", "password": "testpassword"}

    # 1人目のユーザーを作成
    await client.post("/api/v1/users/", json=user_data)

    # 同じユーザー名で2人目を作成
    response = await client.post("/api/v1/users/", json=user_data)

    # レスポンス検証
    assert response.status_code == 400
    assert response.json()["detail"] == "Username or email already registered"


@pytest.mark.asyncio
async def test_login(client: AsyncClient, db_session: AsyncSession):
    """ログインのテスト

    期待する動作:
    - ステータスコード200
    - アクセストークンを返却

    Args:
        client: 非同期HTTPクライアント
        db_session: テスト用DBセッション
    """
    # テストデータ準備
    user_data = {"username": "testuser", "email": "test@example.com", "password": "testpassword"}

    # ユーザーを作成
    await AuthService(db_session).create_user(UserCreate(**user_data))

    # ログイン
    response = await client.post("/api/v1/token", data={"username": user_data["username"], "password": user_data["password"]})

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """無効な認証情報でのログインテスト

    期待する動作:
    - ステータスコード401
    - エラーメッセージを返却

    Args:
        client: 非同期HTTPクライアント
    """
    # テストデータ準備
    invalid_credentials = {"username": "nonexistent", "password": "wrongpassword"}

    # ログイン試行
    response = await client.post("/api/v1/token", data=invalid_credentials)

    # レスポンス検証
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"
