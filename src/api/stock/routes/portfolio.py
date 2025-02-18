from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..schemas import PortfolioSummary, User
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
        - 市場別保有額
        - 通貨別保有額
    """
    portfolio_service = PortfolioService(db)
    return await portfolio_service.get_portfolio_summary(current_user.user_id)


@router.post("/summary", response_model=PortfolioSummary)
async def update_portfolio_summary(
    current_user: Annotated[User, Depends(get_current_user)], db: AsyncSession = Depends(get_db)
):
    """
    ポートフォリオのサマリー情報を更新する
    - ポートフォリオの現在の状態をデータベースに保存
    - 更新された最新のサマリー情報を返却
    """
    portfolio_service = PortfolioService(db)
    await portfolio_service.create_portfolio_history(current_user.user_id)
    return await portfolio_service.get_portfolio_summary(current_user.user_id)
