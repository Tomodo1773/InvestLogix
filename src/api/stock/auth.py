from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, schemas
from .database import get_db, settings

# パスワードハッシュ化のための設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT設定を settings から取得
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


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


async def get_user(db: AsyncSession, username: str):
    """
    ユーザー名からユーザーを取得する
    - db: データベースセッション
    - username: 検索対象のユーザー名
    - 戻り値: 該当ユーザーが存在する場合はUserモデル、存在しない場合はNone
    """
    query = select(models.User).where(models.User.username == username)
    result = await db.execute(query)
    return result.scalar_one_or_none()


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
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> schemas.User:
    """
    現在のユーザーを取得する
    - token: リクエストから取得したJWTトークン
    - db: データベースセッション
    - 戻り値: 認証されたユーザー情報
    - エラー: 認証失敗時は401 Unauthorized
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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
