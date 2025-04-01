from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, status, Request # Request をインポート
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
    request: Request,
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
    # デバッグ情報の追加
    print("=== get_current_user called ===")
    print(f"access_token_cookie: {access_token_cookie}")
    print(f"access_token_cookie type: {type(access_token_cookie)}")
    if access_token_cookie:
        print(f"access_token_cookie starts with 'Bearer ': {access_token_cookie.startswith('Bearer ')}")
    print(f"authorization: {authorization}")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    jwt_token = None  # 初期化して未定義エラーを防止
    
    if access_token_cookie: # if に変更
        # クッキーからトークンを取得（Bearerプレフィックスがある場合は削除）
        if access_token_cookie.startswith("Bearer "):
            jwt_token = access_token_cookie.replace("Bearer ", "")
        else:
            jwt_token = access_token_cookie
        print("クッキートークンを使用")
        print(f"クッキートークン: {jwt_token}")
    elif authorization and authorization.startswith("Bearer "):
        jwt_token = authorization.replace("Bearer ", "")
        print("Authorizationヘッダートークンを使用")
    else:
        print("認証情報が見つかりません")
        raise credentials_exception

    # すべてのリクエストヘッダーを表示
    print("=== リクエストヘッダー ===")
    if request: # 引数のrequestをチェック
        print("Request headers:")
        for key, value in request.headers.items():
            print(f"{key}: {value}")
    else:
        print("Request object not available")

    try:
        if not jwt_token:
            print("jwt_tokenが空です")
            raise credentials_exception
            
        print(f"JWT Token: {jwt_token}")
        payload = jwt.decode(jwt_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            print("トークンにユーザー名が含まれていません")
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError as e:
        print(f"JWTエラー: {e}")
        raise credentials_exception

    user = await get_user(db, username=token_data.username)
    if user is None:
        print(f"ユーザーが見つかりません: {token_data.username}")
        raise credentials_exception
    print(f"認証成功: ユーザー {user.username}")
    return user
