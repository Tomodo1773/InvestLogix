from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from .. import schemas
from ..auth import get_current_user, get_db_for_user
from ..services.stock_split_service import StockSplitService

router = APIRouter()


@router.post("/", response_model=schemas.StockSplit, status_code=status.HTTP_201_CREATED)
async def create_stock_split(
    split: schemas.StockSplitCreate,
    current_user: schemas.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    """
    株式分割を登録する（登録時に過去取引の調整値を自動再計算）

    Args:
        split: 株式分割情報（symbol, split_date, split_ratio）
        current_user: 認証済みユーザー
        db: データベースセッション

    Returns:
        登録された株式分割情報

    Raises:
        StockNotFoundError: 銘柄が未登録の場合（app.pyのハンドラが404に変換する）
        DuplicateStockSplitError: 同一銘柄・同一分割基準日が登録済みの場合（同ハンドラが409に変換する）
    """
    service = StockSplitService(db)
    return await service.create_stock_split(split, current_user.user_id)


@router.get("/", response_model=list[schemas.StockSplit])
async def list_stock_splits(
    symbol: str | None = Query(None, description="銘柄コード（未指定の場合は全銘柄）"),
    current_user: schemas.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    """
    株式分割履歴を取得する

    Args:
        symbol: 銘柄コード（未指定の場合は全銘柄の分割履歴を返却）
        current_user: 認証済みユーザー
        db: データベースセッション

    Returns:
        株式分割履歴のリスト
    """
    service = StockSplitService(db)
    return await service.list_stock_splits(current_user.user_id, symbol)


@router.delete("/{split_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stock_split(
    split_id: int,
    current_user: schemas.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    """
    株式分割を削除する（削除時に調整値を再計算）

    Args:
        split_id: 削除する株式分割ID
        current_user: 認証済みユーザー
        db: データベースセッション

    Raises:
        HTTPException: 分割情報が見つからない場合
    """
    service = StockSplitService(db)
    success = await service.delete_stock_split(split_id, current_user.user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="指定された株式分割情報が見つかりません"
        )


@router.post("/{symbol}/recalculate", status_code=status.HTTP_204_NO_CONTENT)
async def recalculate_adjusted_values(
    symbol: str,
    current_user: schemas.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    """
    指定銘柄の調整値を手動で再計算する

    Args:
        symbol: 銘柄コード
        current_user: 認証済みユーザー
        db: データベースセッション
    """
    service = StockSplitService(db)
    await service.recalculate_adjusted_values(symbol, current_user.user_id)
