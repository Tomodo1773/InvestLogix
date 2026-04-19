"""
日次ジョブ: 全ユーザーの保有銘柄損益を再計算する
Cloud Run Jobs から `python -m stock.jobs.recalc_holdings` で起動する
"""

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User
from ..services.holding_service import update_all_holdings_pl
from ._runner import run_job


async def _action(db: AsyncSession, user: User) -> None:
    await update_all_holdings_pl(db, user.user_id)


def main() -> None:
    run_job(__name__, _action)


if __name__ == "__main__":
    main()
