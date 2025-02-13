from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas


class DividendService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_dividend(self, dividend: schemas.DividendCreate, user_id: int) -> Optional[models.Dividend]:
        # 株式の存在確認
        stock_query = select(models.Stock).where(models.Stock.symbol == dividend.symbol)
        stock_result = await self.db.execute(stock_query)
        stock = stock_result.scalar_one_or_none()

        if not stock:
            return None

        # 配当情報の登録
        db_dividend = models.Dividend(**dividend.model_dump(), user_id=user_id)
        self.db.add(db_dividend)

        # Holdingsテーブルのtotal_dividendを更新
        holdings_query = select(models.Holding).where(
            models.Holding.user_id == user_id, models.Holding.symbol == dividend.symbol
        )
        holdings_result = await self.db.execute(holdings_query)
        holding = holdings_result.scalar_one_or_none()

        if holding:
            # total_dividendに新しい配当金額を加算
            net_dividend = dividend.total_amount
            if dividend.tax is not None:
                net_dividend -= dividend.tax
            if dividend.fee is not None:
                net_dividend -= dividend.fee

            holding.total_dividend = (holding.total_dividend or 0) + net_dividend
            # 未実現損益の更新
            if holding.market_value is not None:
                holding.unrealized_pl = (
                    holding.market_value + (holding.realized_pl or 0) + holding.total_dividend - holding.total_cost
                )
                if holding.total_cost > 0:
                    holding.unrealized_pl_percentage = (holding.unrealized_pl / holding.total_cost) * 100

        await self.db.commit()
        await self.db.refresh(db_dividend)
        return db_dividend

    async def list_dividends(self, user_id: int) -> List[models.Dividend]:
        query = select(models.Dividend).where(models.Dividend.user_id == user_id).order_by(models.Dividend.payment_date.desc())
        result = await self.db.execute(query)
        return result.scalars().all()
