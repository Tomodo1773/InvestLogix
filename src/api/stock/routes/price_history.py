"""
株価時系列データ取得API
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..schemas import PriceHistoryInterval, PriceHistoryResponse
from ..services.price_history_service import PriceHistoryService

router = APIRouter()


@router.get("/{symbol}/price-history", response_model=PriceHistoryResponse)
async def get_price_history(
    symbol: str,
    interval: Annotated[
        PriceHistoryInterval, Query(description="データ間隔（daily, weekly, monthly）")
    ] = PriceHistoryInterval.DAILY,
    limit: Annotated[int, Query(description="取得件数", ge=1, le=500)] = 80,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    指定した銘柄の株価時系列データを取得

    Args:
        symbol: 銘柄コード
        interval: データ間隔（デフォルト: daily）
        limit: 取得件数（デフォルト: 80）
        current_user: 現在のユーザー（認証必須）
        db: データベースセッション

    Returns:
        株価履歴データ

    Raises:
        HTTPException: 銘柄が存在しない、または投資信託など非対応の証券種別の場合
    """
    service = PriceHistoryService(db)

    try:
        result = await service.get_price_history(symbol, interval, limit)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch price history: {str(e)}")
