from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..cloudflare_access import AccessIdentity
from ..models import User, get_jst_now
from ..schemas import UserBase


class UserService:
    """アプリ内ユーザーの解決と登録を行うサービスクラス"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve_by_access_identity(self, identity: AccessIdentity) -> User | None:
        """
        Cloudflare Access の利用者IDからアプリ内ユーザーを解決する
        - identity: 検証済みのAccess利用者ID
        - 戻り値: 対応するユーザー。アプリに登録されていない場合はNone

        Accessが確認済みのメールアドレスを紐付けキーにする。JWTの `sub` は
        Access application ごとに変わりうるためWebとMCPで共通の鍵にできない。
        IdP側でメールアドレスが変わったときは users.email を更新して追随する。
        """
        result = await self.db.execute(select(User).where(User.email == identity.email))
        return result.scalar_one_or_none()

    async def create_user(self, user: UserBase, is_admin: bool = False) -> User:
        """
        新規ユーザーを作成する
        - user: ユーザー作成情報
        - is_admin: 管理者権限を付与するかどうか（デフォルトはFalse）
        - 戻り値: 作成されたユーザーエンティティ

        ここで登録したメールアドレスがCloudflare Accessとの紐付けキーになるため、
        IdP側で使うメールアドレスと一致させる必要がある。
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
