"""
ジョブ共通ランナー
- 対象ユーザーごとにDBセッションを発行して処理を実行する
- 1ユーザーの失敗は記録して次のユーザーへ進む
- ユーザー単位の失敗、または銘柄レベルの価格取得失敗が1件でもあれば終了コード1で終了する
"""

import asyncio
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import AsyncSessionLocal, set_rls_user_id
from ..models import User


@dataclass(frozen=True)
class JobActionResult:
    """ユーザー単位の処理結果。外部通知失敗と銘柄単位失敗を区別して返す。"""

    succeeded: bool = True
    failed_symbols: tuple[str, ...] = ()


UserAction = Callable[[AsyncSession, User], Awaitable[JobActionResult]]

# サマリログに含める失敗銘柄の最大数。これを超えた分は省略件数として記録する
MAX_FAILED_SYMBOLS_IN_LOG = 50


async def _fetch_target_users(notification_users_only: bool) -> list[User]:
    """全ユーザー、またはSlack通知先を登録済みのユーザーを取得する。"""
    async with AsyncSessionLocal() as session:
        query = select(User)
        if notification_users_only:
            query = query.where(User.slack_user_id.is_not(None))
        result = await session.execute(query)
        return list(result.scalars().all())


async def _run_for_each_user(
    job_name: str,
    action: UserAction,
    *,
    notification_users_only: bool,
) -> tuple[int, set[str]]:
    """対象ユーザー全員に対して action を実行し、ユーザー失敗数と失敗銘柄集合を返す"""
    users = await _fetch_target_users(notification_users_only)
    logger.info("ジョブを開始します job={} target_users={}", job_name, len(users))

    failure_count = 0
    failed_symbols: set[str] = set()
    for user in users:
        async with AsyncSessionLocal() as session:
            try:
                await set_rls_user_id(session, user.user_id)
                result = await action(session, user)
                await session.commit()
                failed_symbols.update(result.failed_symbols)
                if result.succeeded:
                    logger.info("ユーザー処理が完了しました job={} user_id={}", job_name, user.user_id)
                else:
                    failure_count += 1
                    logger.error("ユーザー処理が失敗しました job={} user_id={}", job_name, user.user_id)
            except Exception:
                await session.rollback()
                failure_count += 1
                logger.exception("ユーザー処理が失敗しました job={} user_id={}", job_name, user.user_id)

    _log_summary(job_name, len(users), failure_count, failed_symbols)
    return failure_count, failed_symbols


def _log_summary(job_name: str, target_users: int, failure_count: int, failed_symbols: set[str]) -> None:
    """ジョブ末尾のサマリログを構造化して出力する"""
    symbols_sorted = sorted(failed_symbols)
    truncated = symbols_sorted[:MAX_FAILED_SYMBOLS_IN_LOG]
    omitted = max(0, len(symbols_sorted) - MAX_FAILED_SYMBOLS_IN_LOG)
    has_failure = failure_count > 0 or bool(symbols_sorted)
    log = logger.error if has_failure else logger.info
    log(
        "summary action=job_complete job={} target_users={} user_failures={} "
        "failed_symbol_count={} failed_symbols_omitted={} failed_symbols={}",
        job_name,
        target_users,
        failure_count,
        len(symbols_sorted),
        omitted,
        truncated,
    )


def run_job(job_name: str, action: UserAction, *, notification_users_only: bool = False) -> None:
    """ジョブのエントリポイント。ユーザー失敗または失敗銘柄があれば非ゼロで終了する"""
    failure_count, failed_symbols = asyncio.run(
        _run_for_each_user(job_name, action, notification_users_only=notification_users_only)
    )
    if failure_count > 0 or failed_symbols:
        sys.exit(1)
