"""
ジョブ共通ランナー
- LINE連携済みユーザーを対象に、ユーザー単位でDBセッションを発行して処理を実行する
- 1ユーザーの失敗は記録して次のユーザーへ進む
- 1件でも失敗した場合は終了コード1で終了しCloud Run Jobsのリトライ対象にする
"""

import asyncio
import sys
from typing import Awaitable, Callable, List

from loguru import logger
from sqlalchemy import select

from ..database import AsyncSessionLocal, set_rls_user_id
from ..models import User

UserAction = Callable[["AsyncSessionLocal", User], Awaitable[None]]


async def _fetch_target_users() -> List[User]:
    """LINE連携済みユーザーを対象ユーザーとして取得する"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.line_user_id.is_not(None)))
        return list(result.scalars().all())


async def _run_for_each_user(job_name: str, action: UserAction) -> int:
    """対象ユーザー全員に対して action を実行し、失敗件数を返す"""
    users = await _fetch_target_users()
    logger.info("ジョブを開始します job={} target_users={}", job_name, len(users))

    failure_count = 0
    for user in users:
        async with AsyncSessionLocal() as session:
            try:
                await set_rls_user_id(session, user.user_id)
                await action(session, user)
                await session.commit()
                logger.info("ユーザー処理が完了しました job={} user_id={}", job_name, user.user_id)
            except Exception:
                await session.rollback()
                failure_count += 1
                logger.exception("ユーザー処理が失敗しました job={} user_id={}", job_name, user.user_id)

    logger.info(
        "ジョブを終了します job={} target_users={} failures={}",
        job_name,
        len(users),
        failure_count,
    )
    return failure_count


def run_job(job_name: str, action: UserAction) -> None:
    """ジョブのエントリポイント。失敗があれば非ゼロで終了する"""
    failure_count = asyncio.run(_run_for_each_user(job_name, action))
    if failure_count > 0:
        sys.exit(1)
