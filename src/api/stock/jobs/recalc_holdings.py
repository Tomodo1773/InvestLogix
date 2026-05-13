"""
日次ジョブ: 全ユーザーの保有銘柄損益を再計算する
Cloud Run Jobs から `python -m stock.jobs.recalc_holdings` で起動する

実行フロー:
1. 保有中の銘柄について外部APIから直近の価格を取得し price_history に upsert
2. 21日より古い price_history を削除
3. 全 holdings の損益を再計算（価格は price_history から読まれる）
"""

from loguru import logger
from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Holding, Stock, User
from ..schemas import SecurityType
from ..services import price_history_repo
from ..services.holding_service import update_all_holdings_pl
from ..services.stock_price_fetcher import refresh_price_history
from ._runner import run_job

# price_history で保持する最大カレンダー日数（14営業日 + 余裕分）
PRICE_HISTORY_KEEP_DAYS = 21
# 一度に取得する過去日数（営業日換算で 10 日強）
PRICE_HISTORY_FETCH_DAYS = 14


async def _list_active_symbols(db: AsyncSession, user_id: int) -> list[str]:
    """ユーザーが保有中（quantity > 0）の銘柄ユニーク集合を返す"""
    result = await db.execute(
        select(distinct(Holding.symbol)).where(Holding.user_id == user_id, Holding.quantity > 0)
    )
    return [row for row in result.scalars().all()]


async def _refresh_one_symbol(db: AsyncSession, symbol: str) -> bool:
    """1銘柄ぶんの price_history を更新する。成功時 True、失敗時 False"""
    stock = await db.scalar(select(Stock).where(Stock.symbol == symbol))
    if not stock:
        logger.warning("Stockが見つかりませんでした action=select symbol={}", symbol)
        return False

    try:
        upserted = await refresh_price_history(db, stock, days_back=PRICE_HISTORY_FETCH_DAYS)
        await price_history_repo.prune_old_prices(db, symbol, keep_days=PRICE_HISTORY_KEEP_DAYS)
        if upserted == 0 and stock.security_type != SecurityType.FUND.value:
            logger.warning("price_historyのupsertが0件でした action=upsert symbol={}", symbol)
            return False
        return True
    except Exception:
        logger.exception("price_historyの更新に失敗しました action=upsert symbol={}", symbol)
        return False


async def _action(db: AsyncSession, user: User) -> list[str]:
    symbols = await _list_active_symbols(db, user.user_id)

    failed_symbols: set[str] = set()
    for symbol in symbols:
        ok = await _refresh_one_symbol(db, symbol)
        if not ok:
            failed_symbols.add(symbol)

    await db.flush()

    _, holding_failed = await update_all_holdings_pl(db, user.user_id)
    failed_symbols.update(holding_failed)

    return sorted(failed_symbols)


def main() -> None:
    run_job(__name__, _action)


if __name__ == "__main__":
    main()
