from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user, get_db_for_user
from ..schemas import (
    PortfolioHistoryResponse,
    PortfolioSummary,
    User,
    WeeklyPerformanceResponse,
)
from ..services.portfolio_service import PortfolioService
from ..services.weekly_performance_service import calculate_weekly_performance, get_top_bottom_performers
from ..utils.datetime import now_jst

router = APIRouter()


@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    current_user: Annotated[User, Depends(get_current_user)], db: AsyncSession = Depends(get_db_for_user)
):
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
    current_user: Annotated[User, Depends(get_current_user)], db: AsyncSession = Depends(get_db_for_user)
):
    """
    ポートフォリオのサマリー情報を更新する
    - ポートフォリオの現在の状態をデータベースに保存
    - 更新された最新のサマリー情報を返却
    """
    portfolio_service = PortfolioService(db)
    await portfolio_service.create_portfolio_history(current_user.user_id)
    return await portfolio_service.get_portfolio_summary(current_user.user_id)


@router.get("/history", response_model=list[PortfolioHistoryResponse])
async def get_portfolio_history(
    current_user: Annotated[User, Depends(get_current_user)], db: AsyncSession = Depends(get_db_for_user)
):
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


@router.post("/update-and-notify", response_model=dict)
async def update_portfolio_and_notify(
    current_user: Annotated[User, Depends(get_current_user)], db: AsyncSession = Depends(get_db_for_user)
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


@router.get("/weekly-performance", response_model=WeeklyPerformanceResponse)
async def get_weekly_performance(
    current_user: Annotated[User, Depends(get_current_user)], db: AsyncSession = Depends(get_db_for_user)
):
    """
    週間騰落率を取得する（画面表示用、LINE通知は行わない）
    - 保有銘柄の週間騰落率を計算（保有数量が0の銘柄は除外）
    - 投資信託（FUND）は対象外
    - 騰落率の上位・下位5位を抽出
    - 以下の情報を返却:
        - 上位5銘柄の騰落率情報
        - 下位5銘柄の騰落率情報
        - タイムスタンプ
    """
    performances = await calculate_weekly_performance(db, current_user.user_id)
    top_performers, bottom_performers = get_top_bottom_performers(performances, n=5)
    timestamp = now_jst().isoformat()

    return WeeklyPerformanceResponse(
        top_performers=top_performers,
        bottom_performers=bottom_performers,
        all_performers=performances,
        timestamp=timestamp,
    )
