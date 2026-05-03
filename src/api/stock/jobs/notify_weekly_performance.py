"""
週次ジョブ: 全ユーザーの週間騰落率をLINE通知する
Cloud Run Jobs から `python -m stock.jobs.notify_weekly_performance` で起動する
"""

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User
from ..services.notification_service import send_weekly_performance_notification
from ..services.weekly_performance_service import (
    calculate_weekly_performance,
    get_top_bottom_performers,
)
from ._runner import run_job


async def _action(db: AsyncSession, user: User) -> None:
    performances = await calculate_weekly_performance(db, user.user_id)
    top_performers, bottom_performers = get_top_bottom_performers(performances, n=5)
    await send_weekly_performance_notification(
        user_id=user.user_id,
        top_performers=top_performers,
        bottom_performers=bottom_performers,
        db=db,
    )


def main() -> None:
    run_job(__name__, _action)


if __name__ == "__main__":
    main()
