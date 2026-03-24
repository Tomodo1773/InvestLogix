from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..schemas import Stock, StockCreate, User
from ..services.stock_service import StockNotFoundError, StockService

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
        logger.info(
            "Stockに登録しました action=create user_id={} symbol={}",
            current_user.user_id,
            db_stock.symbol,
        )
        return db_stock
    except ValueError:
        raise HTTPException(status_code=404, detail="Stock not found")


@router.get("/", response_model=List[Stock])
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
    stocks = await stock_service.list_stocks(market)
    logger.info(
        "Stockを取得しました action=select user_id={} market={} count={}",
        current_user.user_id,
        market,
        len(stocks),
    )
    return stocks


@router.put("/{symbol}", response_model=Stock)
async def refresh_stock(
    symbol: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    既存銘柄の情報を外部APIから再取得して更新する
    - symbol: 銘柄シンボル
    - 成功時: 更新された銘柄情報を返却
    - 銘柄未登録時: 404 Not Found
    """
    try:
        stock_service = StockService(db)
        db_stock = await stock_service.refresh_stock(symbol)
        logger.info(
            "Stockを更新しました action=update user_id={} symbol={}",
            current_user.user_id,
            db_stock.symbol,
        )
        return db_stock
    except StockNotFoundError:
        raise HTTPException(status_code=404, detail="Stock not found")


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
    logger.info(
        "Stockを削除しました action=delete user_id={} symbol={}",
        current_user.user_id,
        symbol,
    )
    return success
