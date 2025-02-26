from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..auth import get_password_hash
from ..models import User, get_jst_now
from ..schemas import UserCreate


class AuthService:
    """認証関連のサービスクラス"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, user: UserCreate) -> User:
        """
        新規ユーザーを作成する
        - user: ユーザー作成情報
        - 戻り値: 作成されたユーザーエンティティ
        """
        # 既存ユーザーの確認
        result = await self.db.execute(select(User).where((User.username == user.username) | (User.email == user.email)))
        if result.scalar_one_or_none():
            raise ValueError("Username or email already exists")

        # パスワードのハッシュ化
        hashed_password = get_password_hash(user.password)

        # ユーザーの作成
        db_user = User(username=user.username, email=user.email, password_hash=hashed_password, created_at=get_jst_now())
        self.db.add(db_user)
        await self.db.commit()
        return db_user
