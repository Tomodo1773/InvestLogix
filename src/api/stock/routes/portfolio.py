from typing import Annotated, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..schemas import PortfolioHistoryResponse, PortfolioSummary, User
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


@router.get("/history", response_model=List[PortfolioHistoryResponse])
async def get_portfolio_history(current_user: Annotated[User, Depends(get_current_user)], db: AsyncSession = Depends(get_db)):
    """
    ポートフォリオの過去の履歴をすべて取得する
    - 日付順（昇順）でソートされた履歴データを返却
    - 各履歴には以下の情報が含まれる:
        - 記録日時
        - 総コスト
        - 時価評価額
        - 未実現損益
        - 実現損益
        - 配当総額
    """
    portfolio_service = PortfolioService(db)
    return await portfolio_service.get_portfolio_history(current_user.user_id)


@router.post("/update-and-notify", response_model=Dict)
async def update_portfolio_and_notify(
    current_user: Annotated[User, Depends(get_current_user)], db: AsyncSession = Depends(get_db)
):
    """
    ポートフォリオの更新とLINE通知を実行する
    - 全銘柄の株価を最新に更新
    - ポートフォリオの現在の状態をデータベースに保存
    - LINEにポートフォリオの状態を通知
    - 以下の情報を返却:
        - 更新された銘柄数
        - 最新のポートフォリオサマリー
        - 通知送信結果
        - タイムスタンプ
    """
    portfolio_service = PortfolioService(db)
    return await portfolio_service.update_and_notify(current_user.user_id)
