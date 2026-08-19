"""
週次ジョブ: Slack通知先を登録済みの全ユーザーについて、ポートフォリオ更新・履歴保存・通知を実行する
Cloud Run Jobs から `python -m stock.jobs.update_and_notify` で起動する
"""

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User
from ..services.portfolio_service import PortfolioService
from ._runner import JobActionResult, run_job


async def _action(db: AsyncSession, user: User) -> JobActionResult:
    result = await PortfolioService(db).update_and_notify(user.user_id)
    return JobActionResult(succeeded=result["notification_sent"])


def main() -> None:
    run_job(__name__, _action, notification_users_only=True)


if __name__ == "__main__":
    main()
