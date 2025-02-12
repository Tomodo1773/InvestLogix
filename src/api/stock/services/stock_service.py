from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas
from ..jquants import jquants_client


class StockService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_stock(self, stock: schemas.StockCreate) -> Optional[models.Stock]:
        query = select(models.Stock).where(models.Stock.symbol == stock.symbol)
        result = await self.db.execute(query)
        db_stock = result.scalar_one_or_none()

        if db_stock:
            return None

        # Fetch additional stock information from JQuants
        company_info = jquants_client.get_company_info(stock.symbol)
        if not company_info:
            return None

        db_stock = models.Stock(
            symbol=stock.symbol,
            name=company_info.get("CompanyName"),
            name_en=company_info.get("CompanyNameEnglish"),
            market=schemas.StockMarket.JPX,  # Assuming JPX for now
            security_type="STOCK",  # Assuming STOCK for now
            currency="JPY",  # Assuming JPY for now
        )
        self.db.add(db_stock)

        # Create StockJPXDetail
        db_stock_jpx_detail = models.StockJPXDetail(
            symbol=stock.symbol,
            sector_17_code=company_info.get("Sector17Code"),
            sector_17_name=company_info.get("Sector17CodeName"),
            sector_33_code=company_info.get("Sector33Code"),
            sector_33_name=company_info.get("Sector33CodeName"),
            market_segment=company_info.get("MarketCodeName"),
            market_code=company_info.get("ScaleCategory"),
            market_name=company_info.get("MarketCodeName"),
            margin_trading=company_info.get("MarginCode") == "1",
        )
        self.db.add(db_stock_jpx_detail)

        await self.db.commit()
        await self.db.refresh(db_stock)
        return db_stock

    async def list_stocks(self, market: Optional[schemas.StockMarket] = None) -> List[models.Stock]:
        query = select(models.Stock)
        if market:
            query = query.where(models.Stock.market == market)
        result = await self.db.execute(query)
        return result.scalars().all()
