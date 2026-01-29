from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from loguru import logger
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, schemas
from .database import get_db, settings
from .utils.cache import timed_cache

# パスワードハッシュ化のための設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT設定
SECRET_KEY = settings.JWT_SECRET_KEY
# アルゴリズムとトークン有効期限は固定値として定義
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 1日

# OAuth2スキームを更新してOAuthエンドポイントを指すように
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/oauth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    パスワードの検証を行う
    - plain_password: 検証対象の平文パスワード
    - hashed_password: ハッシュ化されたパスワード
    - 戻り値: パスワードが一致する場合True、それ以外はFalse
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    パスワードをハッシュ化する
    - password: ハッシュ化する平文パスワード
    - 戻り値: ハッシュ化されたパスワード
    """
    return pwd_context.hash(password)


@timed_cache(seconds=300)  # 5分間キャッシュする
async def get_user(db: AsyncSession, username: str):
    """
    ユーザー名からユーザーを取得する（キャッシュ機能付き）
    - db: データベースセッション
    - username: 検索対象のユーザー名
    - 戻り値: 該当ユーザーが存在する場合はUserモデル、存在しない場合はNone

    注：キャッシュは5分間有効です。このため、ユーザー情報の変更は最大5分後に反映されます。
    """
    query = select(models.User).where(models.User.username == username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    return user


async def authenticate_user(db: AsyncSession, username: str, password: str):
    """
    ユーザーの認証を行う
    - db: データベースセッション
    - username: 認証対象のユーザー名
    - password: 認証対象のパスワード
    - 戻り値: 認証成功時はUserモデル、失敗時はFalse
    """
    user = await get_user(db, username)

    if not user:
        return False

    if not verify_password(password, user.password_hash):
        return False

    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """
    JWTトークンを生成する
    - data: トークンに含めるデータ（通常はユーザー名）
    - expires_delta: トークンの有効期限（オプション）
    - 戻り値: 生成されたJWTトークン
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    except Exception as e:
        logger.error("JWTトークンのエンコードに失敗しました action=create error={}", str(e))
        raise

    return encoded_jwt


async def get_current_user(
    access_token_cookie: Annotated[str | None, Cookie(alias="token")] = None,
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> schemas.User:
    """
    現在のユーザーを取得する。以下の順序で認証を試みる：
    1. Bearerトークン（OAuth2）
    2. クッキーのアクセストークン
    3. Authorizationヘッダー
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    jwt_token = None  # 初期化して未定義エラーを防止

    if access_token_cookie:  # if に変更
        # クッキーからトークンを取得（Bearerプレフィックスがある場合は削除）
        if access_token_cookie.startswith("Bearer "):
            jwt_token = access_token_cookie.replace("Bearer ", "")
        else:
            jwt_token = access_token_cookie
    elif authorization and authorization.startswith("Bearer "):
        jwt_token = authorization.replace("Bearer ", "")
    else:
        raise credentials_exception

    try:
        if not jwt_token:
            raise credentials_exception

        payload = jwt.decode(jwt_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = await get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def check_admin_privileges(current_user: schemas.User) -> bool:
    """
    ユーザーが管理者権限を持っているかチェックする
    - current_user: 現在のユーザー
    - 戻り値: 管理者の場合はTrue、それ以外はFalse
    """
    return current_user.is_admin


async def get_admin_user(
    current_user: schemas.User = Depends(get_current_user),
) -> schemas.User:
    """
    管理者権限を持つユーザーを取得する
    - 権限がない場合は403エラーを返す
    """
    if not await check_admin_privileges(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to perform this action",
        )
    return current_user
