from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..schemas import Stock, StockCreate, StockWithRelations, User
from ..services.stock_service import StockService

router = APIRouter()


@router.post("/", response_model=Stock)
async def create_stock(
    stock: StockCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    新規銘柄を登録する
    - stock: 銘柄情報（シンボル）
    - 登録成功時: 作成された銘柄情報を返却
    - シンボル重複時: 登録済みの銘柄情報を返却
    - JQuantsから情報取得失敗時: 404 Not Found
    """
    try:
        stock_service = StockService(db)
        db_stock = await stock_service.create_stock(stock)
        return db_stock
    except ValueError:
        raise HTTPException(status_code=404, detail="Stock not found")


@router.get("/", response_model=List[StockWithRelations])
async def list_stocks(
    current_user: Annotated[User, Depends(get_current_user)],
    market: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    登録されている銘柄一覧を取得する
    - market: 市場でフィルタリング（オプション）
    - 成功時: 銘柄情報のリストを返却
    """
    stock_service = StockService(db)
    return await stock_service.list_stocks(market)


@router.delete("/{symbol}", response_model=bool)
async def delete_stock(
    symbol: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    指定されたシンボルの銘柄を削除する
    - symbol: 銘柄シンボル
    - 戻り値: 削除成功時はTrue、失敗時はFalse
    """
    stock_service = StockService(db)
    success = await stock_service.delete_stock(symbol)
    if not success:
        raise HTTPException(status_code=404, detail="Stock not found")
    return success
