"""HTTPフレームワークに依存しない、認証済みユーザーの実行コンテキスト。"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from .cloudflare_access import AccessIdentity
from .database import set_rls_user_id
from .models import User
from .services.user_service import UserService


class UserNotRegisteredError(Exception):
    """Accessでは認証済みだが、InvestLogixに登録されていない利用者。"""


@dataclass(frozen=True)
class UserContext:
    """同じ利用者に束縛されたUserとRLS設定済みDBセッション。"""

    user: User
    db: AsyncSession

    @property
    def user_id(self) -> int:
        return self.user.user_id


async def create_user_context(db: AsyncSession, identity: AccessIdentity) -> UserContext:
    """外部IDをアプリ内ユーザーへ解決し、同じセッションへRLSを設定する。"""
    user = await UserService(db).resolve_by_access_identity(identity)
    if user is None:
        raise UserNotRegisteredError

    await set_rls_user_id(db, user.user_id)
    return UserContext(user=user, db=db)
