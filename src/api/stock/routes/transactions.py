from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..schemas import Transaction, TransactionCreate, User
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
    db_transaction = await transaction_service.create_transaction(transaction, current_user.user_id)
    if not db_transaction:
        if transaction.transaction_type == "sell":
            raise HTTPException(status_code=400, detail="Insufficient shares")
        else:
            raise HTTPException(status_code=404, detail="Stock not found")
    return db_transaction


@router.get("/", response_model=List[Transaction])
async def list_transactions(current_user: Annotated[User, Depends(get_current_user)], db: AsyncSession = Depends(get_db)):
    """
    ユーザーの取引履歴を取得する
    - 成功時: 取引情報のリストを返却（日付降順）
    """
    transaction_service = TransactionService(db)
    return await transaction_service.list_transactions(current_user.user_id)
