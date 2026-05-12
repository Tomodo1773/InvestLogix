"""価格履歴テーブル(price_history)の薄いリポジトリ層。

外部APIは呼ばない。`stock_price_fetcher.py` から DB 読み取り経路として利用される。
"""

from datetime import date, timedelta
from typing import Optional, Sequence

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import PriceHistory, get_jst_now


async def get_recent_prices(db: AsyncSession, symbol: str, days_back: int) -> list[dict]:
    """直近 N カレンダー日分の価格を日付昇順で返す。該当が無ければ空リスト。"""
    threshold = date.today() - timedelta(days=days_back)
    result = await db.execute(
        select(PriceHistory)
        .where(PriceHistory.symbol == symbol)
        .where(PriceHistory.date >= threshold)
        .order_by(PriceHistory.date.asc())
    )
    rows = result.scalars().all()
    return [_row_to_dict(row) for row in rows]


async def get_latest_close(db: AsyncSession, symbol: str) -> Optional[float]:
    """最新営業日の終値を返す。該当が無ければ None。"""
    result = await db.execute(
        select(PriceHistory.close)
        .where(PriceHistory.symbol == symbol)
        .order_by(PriceHistory.date.desc())
        .limit(1)
    )
    value = result.scalar_one_or_none()
    return float(value) if value is not None else None


async def upsert_prices(db: AsyncSession, symbol: str, rows: Sequence[dict]) -> int:
    """ON CONFLICT (symbol, date) DO UPDATE で複数件 upsert。書き込み件数を返す。"""
    if not rows:
        return 0
    now = get_jst_now()
    payload = [
        {
            "symbol": symbol,
            "date": r["date"],
            "open": r["open"],
            "high": r["high"],
            "low": r["low"],
            "close": r["close"],
            "volume": r.get("volume"),
            "last_updated": now,
        }
        for r in rows
    ]
    stmt = pg_insert(PriceHistory).values(payload)
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol", "date"],
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "volume": stmt.excluded.volume,
            "last_updated": stmt.excluded.last_updated,
        },
    )
    await db.execute(stmt)
    return len(payload)


async def prune_old_prices(db: AsyncSession, symbol: str, keep_days: int = 21) -> int:
    """keep_days より古い行を削除。削除件数を返す。"""
    threshold = date.today() - timedelta(days=keep_days)
    result = await db.execute(
        delete(PriceHistory).where(PriceHistory.symbol == symbol).where(PriceHistory.date < threshold)
    )
    return result.rowcount or 0


def _row_to_dict(row: PriceHistory) -> dict:
    return {
        "date": row.date,
        "open": float(row.open),
        "high": float(row.high),
        "low": float(row.low),
        "close": float(row.close),
        "volume": int(row.volume) if row.volume is not None else None,
    }
