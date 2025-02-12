from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas


class StockService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_stock(self, stock: schemas.StockCreate) -> models.Stock:
        query = select(models.Stock).where(models.Stock.symbol == stock.symbol)
        result = await self.db.execute(query)
        db_stock = result.scalar_one_or_none()

        if db_stock:
            return None

        db_stock = models.Stock(**stock.model_dump())
        self.db.add(db_stock)
        await self.db.commit()
        await self.db.refresh(db_stock)
        return db_stock

    async def list_stocks(self, market: Optional[schemas.StockMarket] = None) -> List[models.Stock]:
        query = select(models.Stock)
        if market:
            query = query.where(models.Stock.market == market)
        result = await self.db.execute(query)
        return result.scalars().all()
