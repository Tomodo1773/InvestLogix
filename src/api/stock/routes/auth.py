from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import authenticate_user, create_access_token  # この参照は親モジュールからなので変更なし
from ..database import get_db  # この参照は親モジュールからなので変更なし
from ..schemas import Token, User, UserCreate
from ..services.auth_service import AuthService

router = APIRouter()


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: AsyncSession = Depends(get_db)
):
    """
    ログイントークンを取得する
    - form_data: ユーザー名とパスワード
    - 認証成功時: アクセストークンを返却
    - 認証失敗時: 401 Unauthorized
    """
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
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
