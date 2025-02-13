from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..schemas import Holding
from ..services import holding_service

router = APIRouter()


@router.post("/{symbol}/recalculate", response_model=Holding)
async def recalculate_holding_pl(
    symbol: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """保有株の損益を再計算します。

    Args:
        symbol (str): 銘柄コード
        current_user (User): 認証済みユーザー
        db (AsyncSession): データベースセッション

    Returns:
        Holding: 更新された保有情報
    """
    holding = await holding_service.update_holding_pl(db, current_user.user_id, symbol)
    if not holding:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found in user's holdings")
    return holding
