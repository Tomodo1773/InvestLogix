from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..schemas import LineUserIdUpdate
from ..schemas import User as UserSchema

router = APIRouter()


@router.put("/me/line-user-id", response_model=UserSchema)
async def update_line_user_id(
    line_data: LineUserIdUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    現在ログインしているユーザーのLINE UserIDを更新する

    Args:
        line_data: 更新するLINE UserID情報
        current_user: 現在認証されているユーザー
        db: データベースセッション

    Returns:
        User: 更新されたユーザー情報
    """
    # 現在のユーザー情報を更新
    stmt = update(User).where(User.user_id == current_user.user_id).values(line_user_id=line_data.line_user_id).returning(User)

    result = await db.execute(stmt)
    updated_user = result.scalar_one_or_none()

    if not updated_user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    await db.commit()

    return updated_user
