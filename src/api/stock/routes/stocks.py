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
    - シンボル重複時: 400 Bad Request
    - JQuantsから情報取得失敗時: 404 Not Found
    """
    stock_service = StockService(db)
    db_stock = await stock_service.create_stock(stock)
    if not db_stock:
        raise HTTPException(status_code=400, detail="this symbol already registered")
    return db_stock


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
