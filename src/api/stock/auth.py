"""
FastAPI の認証依存性

本人確認とログインセッションは Cloudflare Access に委譲している。このモジュールは
「Access が検証した外部ID」→「アプリ内ユーザー」→「RLS 用のDBセッション」を繋ぐだけで、
パスワードやトークンの発行は一切持たない。
"""

from fastapi import Depends, HTTPException, Request, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from .cloudflare_access import (
    ACCESS_JWT_HEADER,
    AccessIdentity,
    AccessTokenError,
    authenticate_access_request,
)
from .database import get_db
from .models import User
from .user_context import UserContext, UserNotRegisteredError, create_user_context


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
    token = request.headers.get(ACCESS_JWT_HEADER)
    try:
        return await authenticate_access_request(token)
    except AccessTokenError as e:
        logger.warning("Access JWTの検証に失敗しました action=verify reason={}", str(e))
        raise _unauthenticated() from e


async def get_user_context(
    identity: AccessIdentity = Depends(get_access_identity),
    db: AsyncSession = Depends(get_db),
) -> UserContext:
    """
    認証済みの外部IDからアプリ内ユーザーを取得する
    - アプリに登録されていない利用者の場合: 403 Forbidden
    """
    try:
        return await create_user_context(db, identity)
    except UserNotRegisteredError as e:
        logger.warning("Access IDに対応するUserがいません action=select email={}", identity.email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このアカウントはInvestLogixに登録されていません",
        ) from e


async def get_current_user(context: UserContext = Depends(get_user_context)) -> User:
    """認証・ユーザー解決済みコンテキストから利用者を返す。"""
    return context.user


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


async def get_db_for_user(context: UserContext = Depends(get_user_context)) -> AsyncSession:
    """
    RLS用のuser_idを設定したデータベースセッションを返す依存性注入
    - 認証済みユーザーのuser_idをPostgreSQLセッション変数に設定する
    - 使用例: db: AsyncSession = Depends(get_db_for_user)
    """
    return context.db
