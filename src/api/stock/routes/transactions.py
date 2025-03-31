from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..schemas import MonthlySummary, Transaction, TransactionCreate, User
from ..services.stock_service import StockNotFoundError
from ..services.transaction_service import TransactionService

router = APIRouter()


@router.post("/", response_model=Transaction)
async def create_transaction(
    transaction: TransactionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    新規取引を登録する
    - transaction: 取引情報（銘柄、数量、価格、取引種別等）
    - 登録成功時: 作成された取引情報を返却
    - 銘柄不存在時: 404 Not Found
    - 売却時の保有数量不足: 400 Bad Request
    """
    transaction_service = TransactionService(db)
    try:
        db_transaction = await transaction_service.create_transaction(transaction, current_user.user_id)
        if not db_transaction:
            raise HTTPException(status_code=400, detail="Insufficient shares")
        return db_transaction
    except StockNotFoundError:
        raise HTTPException(status_code=404, detail="Stock not found")


@router.get("/", response_model=List[Transaction])
async def list_transactions(current_user: Annotated[User, Depends(get_current_user)], db: AsyncSession = Depends(get_db)):
    """
    ユーザーの取引履歴を取得する
    - 成功時: 取引情報のリストを返却（日付降順）
    """
    transaction_service = TransactionService(db)
    return await transaction_service.list_transactions(current_user.user_id)


@router.get("/monthly-summary", response_model=List[MonthlySummary])
async def get_monthly_transaction_summary(
    current_user: Annotated[User, Depends(get_current_user)], db: AsyncSession = Depends(get_db)
):
    """
    月ごとのトランザクション集計を取得する

    Returns:
        List[MonthlySummary]: 月ごとの口座種別別購入金額集計
    """
    transaction_service = TransactionService(db)
    return await transaction_service.get_monthly_summary(current_user.user_id)
