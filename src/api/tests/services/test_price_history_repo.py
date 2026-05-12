"""price_history_repo のテスト"""

from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from stock.models import Stock
from stock.services import price_history_repo


async def _create_stock(db: AsyncSession, symbol: str = "8058") -> Stock:
    stock = Stock(
        symbol=symbol,
        name="テスト銘柄",
        market="JPX",
        security_type="STOCK",
        currency="JPY",
    )
    db.add(stock)
    await db.flush()
    return stock


def _make_row(d: date, close: float = 100.0) -> dict:
    return {
        "date": d,
        "open": close,
        "high": close + 5,
        "low": close - 5,
        "close": close,
        "volume": 10000,
    }


@pytest.mark.asyncio
async def test_upsert_and_get_recent_prices(db_session: AsyncSession):
    """upsert した行が get_recent_prices で日付昇順で返ること"""
    await _create_stock(db_session)
    today = date.today()
    rows = [_make_row(today - timedelta(days=i), close=100.0 + i) for i in range(3)]

    written = await price_history_repo.upsert_prices(db_session, "8058", rows)
    assert written == 3

    fetched = await price_history_repo.get_recent_prices(db_session, "8058", days_back=5)
    assert len(fetched) == 3
    assert fetched[0]["date"] < fetched[-1]["date"]


@pytest.mark.asyncio
async def test_upsert_overwrites_existing_date(db_session: AsyncSession):
    """同じ (symbol, date) を再 upsert すると値が上書きされること"""
    await _create_stock(db_session)
    today = date.today()
    await price_history_repo.upsert_prices(db_session, "8058", [_make_row(today, close=100.0)])
    await price_history_repo.upsert_prices(db_session, "8058", [_make_row(today, close=200.0)])

    fetched = await price_history_repo.get_recent_prices(db_session, "8058", days_back=1)
    assert len(fetched) == 1
    assert fetched[0]["close"] == 200.0


@pytest.mark.asyncio
async def test_get_latest_close_returns_most_recent(db_session: AsyncSession):
    """get_latest_close は最新営業日の close を返すこと"""
    await _create_stock(db_session)
    today = date.today()
    rows = [
        _make_row(today - timedelta(days=2), close=100.0),
        _make_row(today - timedelta(days=1), close=110.0),
        _make_row(today, close=120.0),
    ]
    await price_history_repo.upsert_prices(db_session, "8058", rows)

    latest = await price_history_repo.get_latest_close(db_session, "8058")
    assert latest == 120.0


@pytest.mark.asyncio
async def test_get_latest_close_returns_none_when_empty(db_session: AsyncSession):
    """データが無い銘柄では None を返すこと"""
    await _create_stock(db_session)
    latest = await price_history_repo.get_latest_close(db_session, "8058")
    assert latest is None


@pytest.mark.asyncio
async def test_prune_old_prices_removes_only_old_rows(db_session: AsyncSession):
    """keep_days を超える行のみ削除されること"""
    await _create_stock(db_session)
    today = date.today()
    rows = [
        _make_row(today - timedelta(days=30), close=100.0),
        _make_row(today - timedelta(days=10), close=110.0),
        _make_row(today, close=120.0),
    ]
    await price_history_repo.upsert_prices(db_session, "8058", rows)

    deleted = await price_history_repo.prune_old_prices(db_session, "8058", keep_days=21)
    assert deleted == 1

    remaining = await price_history_repo.get_recent_prices(db_session, "8058", days_back=60)
    assert len(remaining) == 2
