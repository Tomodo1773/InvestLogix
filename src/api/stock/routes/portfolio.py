from typing import Annotated, List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..schemas import Holding, PortfolioSummary, User
from ..services.portfolio_service import PortfolioService

router = APIRouter()


@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(current_user: Annotated[User, Depends(get_current_user)], db: AsyncSession = Depends(get_db)):
    """
    ポートフォリオのサマリー情報を取得する
    - 取得情報:
        - 総コスト
        - 総時価評価額
        - 未実現損益
        - 実現損益
        - 配当総額
        - 現金残高
        - 市場別保有額
        - 通貨別保有額
    """
    portfolio_service = PortfolioService(db)
    return await portfolio_service.get_portfolio_summary(current_user.user_id)


@router.get("/holdings/", response_model=List[Holding])
async def list_holdings(current_user: Annotated[User, Depends(get_current_user)], db: AsyncSession = Depends(get_db)):
    """
    ユーザーの保有銘柄一覧を取得する
    - 取得情報:
        - シンボル
        - 数量
        - 平均取得単価
        - 取得総額
        - 時価評価額
    """
    portfolio_service = PortfolioService(db)
    return await portfolio_service.list_holdings(current_user.user_id)
