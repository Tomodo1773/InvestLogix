"""
FastAPI の認証依存性

本人確認とログインセッションは Cloudflare Access に委譲している。このモジュールは
「Access が検証した外部ID」→「アプリ内ユーザー」→「RLS 用のDBセッション」を繋ぐだけで、
パスワードやトークンの発行は一切持たない。
"""

from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from .cloudflare_access import ACCESS_JWT_HEADER, AccessIdentity, AccessTokenError, verify_access_token
from .database import get_db, set_rls_user_id, settings
from .models import User
from .services.user_service import UserService

# ローカル開発用の擬似Accessの issuer。実在しないドメインにして本番のIDと衝突させない
DEV_ACCESS_ISSUER = "https://dev.invalid"


def _unauthenticated() -> HTTPException:
    """未認証の応答。理由（ヘッダー欠落か署名不正か）は攻撃者に手掛かりを与えないため区別しない"""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証が必要です",
    )


async def get_access_identity(request: Request) -> AccessIdentity:
    """
    Cloudflare Access が付与したJWTを検証して外部IDを返す

    アプリ全体の依存性として登録する（app.py）。個々のルートが認証を書き忘れても
    素通りしないようにするためで、ルート側の get_current_user とは結果を共有する。
    Cloudflare を迂回した直アクセスはヘッダーが無いか署名が不正なので、ここで落ちる。
    """
    if settings.DEV_AUTH_EMAIL:
        # ローカル開発ではCloudflareを経由しないため、擬似的な外部IDを組み立てる。
        # 本番でこの値が設定されていた場合は Settings の検証で起動時に失敗する
        return AccessIdentity(
            issuer=DEV_ACCESS_ISSUER,
            subject=settings.DEV_AUTH_EMAIL,
            email=settings.DEV_AUTH_EMAIL,
        )

    token = request.headers.get(ACCESS_JWT_HEADER)
    if not token:
        raise _unauthenticated()

    try:
        return await verify_access_token(token)
    except AccessTokenError as e:
        logger.warning("Access JWTの検証に失敗しました action=verify reason={}", str(e))
        raise _unauthenticated() from e


async def get_current_user(
    identity: AccessIdentity = Depends(get_access_identity),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    認証済みの外部IDからアプリ内ユーザーを取得する
    - アプリに登録されていない利用者の場合: 403 Forbidden
    """
    user = await UserService(db).resolve_by_access_identity(identity)
    if user is None:
        logger.warning("Access IDに対応するUserがいません action=select email={}", identity.email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このアカウントはInvestLogixに登録されていません",
        )
    return user


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    管理者権限を持つユーザーを取得する
    - 権限がない場合: 403 Forbidden
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理者権限が必要です",
        )
    return current_user


async def get_db_for_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[AsyncSession]:
    """
    RLS用のuser_idを設定したデータベースセッションを返す依存性注入
    - 認証済みユーザーのuser_idをPostgreSQLセッション変数に設定する
    - 使用例: db: AsyncSession = Depends(get_db_for_user)
    """
    await set_rls_user_id(db, current_user.user_id)
    yield db
