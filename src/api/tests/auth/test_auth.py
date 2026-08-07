import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from stock.schemas import UserCreate
from stock.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient, auth_admin_token: str, db_session: AsyncSession):
    """新規ユーザー登録のテスト

    期待する動作:
    - ステータスコード200
    - 作成されたユーザー情報を返却
    - パスワードハッシュが含まれない

    Args:
        client: 非同期HTTPクライアント
        auth_admin_token: 管理者権限を持つユーザーのトークン
        db_session: テスト用DBセッション
    """
    # テストデータ準備
    user_data = {"username": "testuser2", "email": "test2@example.com", "password": "testpassword"}

    # APIリクエスト実行（Authorizationヘッダーを追加）
    response = await client.post("/api/v1/users/", json=user_data)

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_create_duplicate_user(client: AsyncClient, auth_admin_token: str, db_session: AsyncSession):
    """重複ユーザー登録のテスト

    期待する動作:
    - ステータスコード400
    - エラーメッセージを返却

    Args:
        client: 非同期HTTPクライアント
        auth_admin_token: 管理者権限を持つユーザーのトークン
        db_session: テスト用DBセッション
    """
    # テストデータ準備
    user_data = {"username": "testuser3", "email": "test3@example.com", "password": "testpassword"}

    # 1人目のユーザーを作成
    await client.post("/api/v1/users/", json=user_data)

    # 同じユーザー名で2人目を作成
    response = await client.post("/api/v1/users/", json=user_data)

    # レスポンス検証
    assert response.status_code == 400
    assert response.json()["detail"] == "Username or email already registered"


@pytest.mark.asyncio
async def test_create_user_without_admin_privileges(
    client: AsyncClient, auth_token: str, db_session: AsyncSession
):
    """管理者権限なしでのユーザー登録のテスト

    期待する動作:
    - ステータスコード403
    - 権限エラーメッセージを返却

    Args:
        client: 非同期HTTPクライアント
        auth_token: 一般ユーザーの認証トークン
        db_session: テスト用DBセッション
    """
    # テストデータ準備
    user_data = {"username": "newuser", "email": "newuser@example.com", "password": "newpassword"}

    # 管理者権限なしでリクエスト実行
    response = await client.post("/api/v1/users/", json=user_data)

    # レスポンス検証
    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator privileges required"


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
    user_data = {
        "username": "admin",
        "email": "test_admin@example.com",
        "password": "adminpassword",
        "is_admin": True,
    }

    # ユーザーを作成（サービス層はflush()のみのため、テストでは明示的にcommitが必要）
    await AuthService(db_session).create_user(UserCreate(**user_data))
    await db_session.commit()

    # ログイン（JSON形式でリクエスト）
    login_data = {"username": user_data["username"], "password": user_data["password"]}
    response = await client.post("/api/v1/token", json=login_data)

    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, auth_token: None):
    """ログアウトのテスト

    期待する動作:
    - ステータスコード204
    - Set-Cookieでtokenが失効する（発行時と同じ path / samesite 属性が付く）
    - ログアウト後は認証が必要なエンドポイントが401になる

    Args:
        client: 非同期HTTPクライアント
        auth_token: 一般ユーザーの認証フィクスチャ（clientにCookieをセットする副作用）
    """
    # ログアウト前はCookie認証が通ることを確認
    assert (await client.get("/api/v1/me")).status_code == 200

    response = await client.post("/api/v1/logout")

    # レスポンス検証
    assert response.status_code == 204
    set_cookie = response.headers["set-cookie"]
    assert "token=" in set_cookie
    assert "Max-Age=0" in set_cookie
    # 発行時と属性が食い違うとブラウザ側で削除が効かないため、set_cookieと揃っていることを確認
    assert "Path=/" in set_cookie
    assert "SameSite=lax" in set_cookie

    # Cookieが破棄され、セッションが終了していることを確認
    assert "token" not in client.cookies
    assert (await client.get("/api/v1/me")).status_code == 401


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

    # ログイン試行（JSON形式でリクエスト）
    response = await client.post("/api/v1/token", json=invalid_credentials)

    # レスポンス検証
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"
