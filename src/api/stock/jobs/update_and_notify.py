"""
週次ジョブ: 全ユーザーのポートフォリオ更新・履歴保存・LINE Flex通知を実行する
Cloud Run Jobs から `python -m stock.jobs.update_and_notify` で起動する
"""

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User
from ..services.portfolio_service import PortfolioService
from ._runner import run_job


async def _action(db: AsyncSession, user: User) -> None:
    await PortfolioService(db).update_and_notify(user.user_id)


def main() -> None:
    run_job(__name__, _action)


if __name__ == "__main__":
    main()
