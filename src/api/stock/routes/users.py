from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_admin_user, get_current_user
from ..database import get_db
from ..models import User
from ..schemas import SlackUserIdUpdate, UserBase
from ..schemas import User as UserSchema
from ..services.user_service import UserService

router = APIRouter()


@router.get("/me", response_model=UserSchema)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    現在ログインしているユーザーを返す
    - 認証はCloudflare Accessが行い、ここではアプリ内ユーザーへの解決結果を返すだけ
    - 未認証: 401 Unauthorized / アプリ未登録: 403 Forbidden
    """
    return current_user


@router.put("/me/slack-user-id", response_model=UserSchema)
async def update_slack_user_id(
    slack_data: SlackUserIdUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    現在ログインしているユーザーのSlack User IDを更新する
    - slack_data: 更新するSlack User ID情報
    - 戻り値: 更新されたユーザー情報
    """
    stmt = (
        update(User)
        .where(User.user_id == current_user.user_id)
        .values(slack_user_id=slack_data.slack_user_id)
        .returning(User)
    )

    result = await db.execute(stmt)
    updated_user = result.scalar_one_or_none()

    if not updated_user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    return updated_user


@router.post("/", response_model=UserSchema)
async def create_user(
    user: UserBase,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
):
    """
    新規ユーザーを登録する（管理者のみ実行可能）
    - user: ユーザー情報（ユーザー名、メールアドレス）
    - ここで登録したメールアドレスでAccessログインすると、初回に外部IDが紐付く
    - ユーザー名/メールアドレス重複時: 400 Bad Request
    - 管理者権限がない場合: 403 Forbidden
    """
    try:
        return await UserService(db).create_user(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
