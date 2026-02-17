from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user, get_db_for_user
from ..models import User
from ..schemas import Holding
from ..services import holding_service

router = APIRouter()


@router.post("/{symbol}/recalculate", response_model=Holding)
async def recalculate_holding_pl(
    symbol: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_for_user)
):
    """
    保有株の損益を再計算します。

    Args:
        symbol (str): 銘柄コード
        current_user (User): 認証済みユーザー
        db (AsyncSession): データベースセッション

    Returns:
        Holding: 更新された保有情報
    """
    holding = await holding_service.update_single_holding_pl(db, current_user.user_id, symbol)
    if not holding:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found in user's holdings")
    return holding


@router.get("/", response_model=List[Holding])
async def list_holdings(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db_for_user),
    symbol: Optional[str] = Query(None, description="フィルタリングする銘柄コード"),
):
    """
    ユーザーの保有銘柄一覧を取得する
    - symbol: 特定の銘柄コードでフィルタリングする場合に指定（オプション）
    - 成功時: 保有銘柄情報のリストを返却
    """
    return await holding_service.list_holdings(db, current_user.user_id, symbol)


@router.post("/recalculate-all", response_model=List[Holding])
async def recalculate_all_holdings_pl(
    current_user: Annotated[User, Depends(get_current_user)], db: AsyncSession = Depends(get_db_for_user)
):
    """
    保有する全銘柄の損益を一括で再計算します。
    各銘柄の更新は非同期で並行処理されます。

    Args:
        current_user (User): 認証済みユーザー
        db (AsyncSession): データベースセッション

    Returns:
        List[Holding]: 更新された保有情報のリスト
    """
    return await holding_service.update_all_holdings_pl(db, current_user.user_id)
