from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from loguru import logger

from ..auth import get_password_hash
from ..models import User, get_jst_now
from ..schemas import UserCreate


class AuthService:
    """認証関連のサービスクラス"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, user: UserCreate, is_admin: bool = False) -> User:
        """
        新規ユーザーを作成する
        - user: ユーザー作成情報
        - is_admin: 管理者権限を付与するかどうか（デフォルトはFalse）
        - 戻り値: 作成されたユーザーエンティティ
        """
        # 既存ユーザーの確認
        result = await self.db.execute(
            select(User).where((User.username == user.username) | (User.email == user.email))
        )
        if result.scalar_one_or_none():
            logger.error("Userが既に存在します action=select reason=already_exists")
            raise ValueError("Username or email already registered")

        # パスワードのハッシュ化
        hashed_password = get_password_hash(user.password)

        # ユーザーの作成（is_admin フラグも設定）
        db_user = User(
            username=user.username,
            email=user.email,
            password_hash=hashed_password,
            created_at=get_jst_now(),
            is_admin=is_admin,
        )
        self.db.add(db_user)
        await self.db.commit()
        logger.info("Userを登録しました action=create user_id={}", db_user.user_id)
        return db_user
