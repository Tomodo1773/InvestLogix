from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas


class DividendService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_dividend(self, dividend: schemas.DividendCreate, user_id: int) -> Optional[models.Dividend]:
        stock_query = select(models.Stock).where(models.Stock.symbol == dividend.symbol)
        stock_result = await self.db.execute(stock_query)
        stock = stock_result.scalar_one_or_none()

        if not stock:
            return None

        db_dividend = models.Dividend(**dividend.model_dump(), user_id=user_id)
        self.db.add(db_dividend)
        await self.db.commit()
        await self.db.refresh(db_dividend)
        return db_dividend

    async def list_dividends(self, user_id: int) -> List[models.Dividend]:
        query = select(models.Dividend).where(models.Dividend.user_id == user_id).order_by(models.Dividend.payment_date.desc())
        result = await self.db.execute(query)
        return result.scalars().all()
