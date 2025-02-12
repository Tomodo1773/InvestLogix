from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..schemas import Dividend, DividendCreate, User
from ..services.dividend_service import DividendService

router = APIRouter()


@router.post("/", response_model=Dividend)
async def create_dividend(
    dividend: DividendCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    配当情報を登録する
    - dividend: 配当情報（銘柄、配当額、配当日等）
    - 登録成功時: 作成された配当情報を返却
    - 銘柄不存在時: 404 Not Found
    """
    dividend_service = DividendService(db)
    db_dividend = await dividend_service.create_dividend(dividend, current_user.user_id)
    if not db_dividend:
        raise HTTPException(status_code=404, detail="Stock not found")
    return db_dividend


@router.get("/", response_model=List[Dividend])
async def list_dividends(current_user: Annotated[User, Depends(get_current_user)], db: AsyncSession = Depends(get_db)):
    """
    ユーザーの配当履歴を取得する
    - 成功時: 配当情報のリストを返却（支払日降順）
    """
    dividend_service = DividendService(db)
    return await dividend_service.list_dividends(current_user.user_id)
