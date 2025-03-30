from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import (  # get_current_userをインポート
    authenticate_user,
    create_access_token,
    get_current_user,
)
from ..database import get_db  # この参照は親モジュールからなので変更なし
from ..schemas import LoginRequest, Token, User, UserCreate
from ..services.auth_service import AuthService

router = APIRouter()


@router.post("/token", response_model=Token)
async def login_for_access_token(response: Response, login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    ログイントークンを取得する
    - login_data: ユーザー名とパスワード（JSON形式）
    - 認証成功時: アクセストークンを返却（レスポンスボディとクッキーの両方）
    - 認証失敗時: 401 Unauthorized
    """
    user = await authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})

    # HTTPOnlyクッキーにトークンを設定
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=True,  # HTTPS環境での使用を想定
        samesite="strict",
        max_age=3600,  # 1時間
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/oauth/token", response_model=Token)
async def login_for_access_token_oauth(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """
    OAuth2形式でログイントークンを取得する（/docsでの認証用）
    - form_data: ユーザー名とパスワード（application/x-www-form-urlencoded形式）
    - 認証成功時: アクセストークンを返却
    - 認証失敗時: 401 Unauthorized

    このエンドポイントはFastAPIの/docsページの「authorize」ボタンで使用するための最小限の実装です。
    """
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})

    # シンプルなトークンレスポンスのみを返す
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/users/", response_model=User)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    新規ユーザーを登録する
    - user: ユーザー情報（ユーザー名、メールアドレス、パスワード）
    - 登録成功時: 作成されたユーザー情報を返却
    - ユーザー名/メールアドレス重複時: 400 Bad Request
    """
    auth_service = AuthService(db)
    try:
        db_user = await auth_service.create_user(user)
        return db_user
    except ValueError:
        # ValueErrorの内容に関わらず統一したエラーメッセージを返す
        raise HTTPException(status_code=400, detail="Username or email already registered")


@router.get("/me", response_model=User)
async def verify_token(current_user: User = Depends(get_current_user)):
    """
    現在のユーザーの認証状態を確認する
    - トークンはCookieから取得（get_current_userで処理）
    - 認証成功時: ユーザー情報を返却
    - 認証失敗時: 401 Unauthorized（get_current_user内で例外発生）
    """
    return current_user
