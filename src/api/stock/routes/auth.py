from fastapi import APIRouter, Depends, HTTPException, Response, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import ACCESS_TOKEN_EXPIRE_MINUTES, authenticate_user, create_access_token, get_current_user
from ..database import get_db, settings
from ..schemas import LoginRequest, Token, User, UserCreate
from ..services.auth_service import AuthService

router = APIRouter()

TOKEN_COOKIE_NAME = "token"

# フロントとAPIは同一オリジン（Cloudflare Workerが /api/* を転送する）なので
# このCookieはサードパーティCookieにならない。よって samesite=lax で足りる。
# Secure だけは本番のみ有効にする（ローカルはhttpで開発するため）
#
# 削除時に発行と同じ属性を渡さないとブラウザ側でCookieが消えないことがあるため、
# 発行(set_cookie)と削除(delete_cookie)で属性を共有する。
TOKEN_COOKIE_ATTRS = {
    "path": "/",
    "httponly": True,
    "secure": settings.ENVIRONMENT.lower() == "production",
    "samesite": "lax",
}


@router.post("/token", response_model=Token)
async def login_for_access_token(
    response: Response, login_data: LoginRequest, db: AsyncSession = Depends(get_db)
):
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
        )

    access_token = create_access_token(data={"sub": user.username})

    response.set_cookie(
        key=TOKEN_COOKIE_NAME,
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # 分を秒に変換
        **TOKEN_COOKIE_ATTRS,
    )
    logger.info("Authトークンを発行しました action=create user_id={}", user.user_id)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    """
    ログアウトする
    - 認証Cookieを削除する
    - 認証は不要（Cookieを消すだけの操作なので、未認証で叩かれても無害）
    """
    response.delete_cookie(key=TOKEN_COOKIE_NAME, **TOKEN_COOKIE_ATTRS)
    logger.info("Authトークンを削除しました action=delete")


@router.post("/users/", response_model=User)
async def create_user(
    user: UserCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    新規ユーザーを登録する（管理者のみ実行可能）
    - user: ユーザー情報（ユーザー名、メールアドレス、パスワード）
    - 登録成功時: 作成されたユーザー情報を返却
    - ユーザー名/メールアドレス重複時: 400 Bad Request
    - 管理者権限がない場合: 403 Forbidden
    """
    # まず管理者権限をチェック
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )

    # 管理者確認後、ユーザー作成処理を実行
    auth_service = AuthService(db)
    try:
        db_user = await auth_service.create_user(user)
        return db_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me", response_model=User)
async def verify_token(current_user: User = Depends(get_current_user)):
    """
    現在のユーザーの認証状態を確認する
    - トークンはCookieから取得（get_current_userで処理）
    - 認証成功時: ユーザー情報を返却
    - 認証失敗時: 401 Unauthorized（get_current_user内で例外発生）
    """
    return current_user
