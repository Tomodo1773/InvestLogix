"""recalc_holdings ジョブのテスト"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from stock.jobs.recalc_holdings import _action
from stock.models import Holding, Stock, User
from stock.services import price_history_repo


async def _seed_user_with_holding(db: AsyncSession, symbol: str = "8058") -> User:
    user = User(
        username="job_testuser",
        email="job@example.com",
        line_user_id="U_JOB",
    )
    db.add(user)
    await db.flush()

    stock = Stock(
        symbol=symbol,
        name="テスト銘柄",
        market="JPX",
        security_type="STOCK",
        currency="JPY",
    )
    db.add(stock)
    await db.flush()

    db.add(
        Holding(
            user_id=user.user_id,
            symbol=symbol,
            quantity=100.0,
            average_cost=3000.0,
            total_cost=300000.0,
        )
    )
    await db.flush()
    return user


@pytest.mark.asyncio
async def test_action_refreshes_price_history(db_session: AsyncSession, mock_external_apis):
    """ジョブ実行で price_history に複数日のレコードが入ること"""
    user = await _seed_user_with_holding(db_session, symbol="8058")

    failed = await _action(db_session, user)

    assert failed == []
    rows = await price_history_repo.get_recent_prices(db_session, "8058", days_back=30)
    assert len(rows) >= 6  # MOCK_JQUANTS_PRICE_DATA は 7 日分


@pytest.mark.asyncio
async def test_action_marks_failed_symbol_on_external_api_error(db_session: AsyncSession, mock_external_apis):
    """外部APIで例外が発生した銘柄が failed_symbols に含まれること"""
    user = await _seed_user_with_holding(db_session, symbol="8058")
    mock_external_apis["jquants_client"].get_prices.side_effect = Exception("simulated error")

    failed = await _action(db_session, user)
    assert "8058" in failed
