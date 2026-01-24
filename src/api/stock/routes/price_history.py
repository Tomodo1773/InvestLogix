"""
株価時系列データ取得API
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..schemas import PriceHistoryInterval, PriceHistoryPeriod, PriceHistoryResponse
from ..services.price_history_service import PriceHistoryService

router = APIRouter()


@router.get("/{symbol}/price-history", response_model=PriceHistoryResponse)
async def get_price_history(
    symbol: str,
    period: Annotated[
        PriceHistoryPeriod, Query(description="取得期間（1M, 3M, 6M, 1Y, 3Y）")
    ] = PriceHistoryPeriod.ONE_YEAR,
    interval: Annotated[
        PriceHistoryInterval, Query(description="データ間隔（daily, weekly, monthly）")
    ] = PriceHistoryInterval.DAILY,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    指定した銘柄の株価時系列データを取得

    Args:
        symbol: 銘柄コード
        period: 取得期間（デフォルト: 1Y）
        interval: データ間隔（デフォルト: daily）
        current_user: 現在のユーザー（認証必須）
        db: データベースセッション

    Returns:
        株価履歴データ

    Raises:
        HTTPException: 銘柄が存在しない、または投資信託など非対応の証券種別の場合
    """
    service = PriceHistoryService(db)

    try:
        result = await service.get_price_history(symbol, period, interval)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch price history: {str(e)}")
