from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas
from ..auth import get_password_hash


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, user: schemas.UserCreate) -> models.User:
        query = select(models.User).where((models.User.username == user.username) | (models.User.email == user.email))
        result = await self.db.execute(query)
        db_user = result.scalar_one_or_none()

        if db_user:
            return None

        hashed_password = get_password_hash(user.password)
        db_user = models.User(username=user.username, email=user.email, password_hash=hashed_password)
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        return db_user
