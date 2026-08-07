from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..cloudflare_access import AccessIdentity
from ..models import User, get_jst_now
from ..schemas import UserCreate


class UserService:
    """アプリ内ユーザーの解決と登録を行うサービスクラス"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve_by_access_identity(self, identity: AccessIdentity) -> User | None:
        """
        Cloudflare Access の外部IDからアプリ内ユーザーを解決する
        - identity: 検証済みのAccess外部ID
        - 戻り値: 対応するユーザー。アプリに登録されていない場合はNone

        通常は (issuer, subject) の紐付けで引く。subject はIdP側でメールアドレスが
        変わっても不変なため、恒久的な紐付けキーとして使える。
        まだ紐付いていないユーザーは、Accessが確認済みのメールアドレスで初回だけ紐付ける。
        """
        user = await self._find_by_access_identity(identity)
        if user:
            return user

        user = await self._find_unlinked_by_email(identity.email)
        if user is None:
            return None

        user.access_issuer = identity.issuer
        user.access_subject = identity.subject
        await self.db.flush()
        logger.info("UserをAccess IDへ紐付けました action=update user_id={}", user.user_id)
        return user

    async def create_user(self, user: UserCreate, is_admin: bool = False) -> User:
        """
        新規ユーザーを作成する
        - user: ユーザー作成情報
        - is_admin: 管理者権限を付与するかどうか（デフォルトはFalse）
        - 戻り値: 作成されたユーザーエンティティ

        Access IDはまだ紐付けない。作成したメールアドレスで初回ログインしたときに
        resolve_by_access_identity が紐付ける。
        """
        result = await self.db.execute(
            select(User).where((User.username == user.username) | (User.email == user.email))
        )
        if result.scalar_one_or_none():
            logger.error("Userが既に存在します action=select reason=already_exists")
            raise ValueError("Username or email already registered")

        db_user = User(
            username=user.username,
            email=user.email,
            created_at=get_jst_now(),
            is_admin=is_admin,
        )
        self.db.add(db_user)
        await self.db.flush()
        logger.info("Userを登録しました action=create user_id={}", db_user.user_id)
        return db_user

    async def _find_by_access_identity(self, identity: AccessIdentity) -> User | None:
        result = await self.db.execute(
            select(User).where(
                User.access_issuer == identity.issuer,
                User.access_subject == identity.subject,
            )
        )
        return result.scalar_one_or_none()

    async def _find_unlinked_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email, User.access_subject.is_(None)))
        return result.scalar_one_or_none()
