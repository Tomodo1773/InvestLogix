import re
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas
from ..jquants import jquants_client
from .alphavantage_service import (
    fetch_us_stock_overview,
    fetch_us_stock_search,
    fetch_usdjpy_rate,
)
from .investment_trust_service import fetch_investment_trust_details


class StockService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_stock(self, stock: schemas.StockCreate) -> Optional[models.Stock]:
        query = select(models.Stock).where(models.Stock.symbol == stock.symbol)
        result = await self.db.execute(query)
        db_stock = result.scalar_one_or_none()

        if db_stock:
            return None

        if self.is_investment_trust(stock.symbol):
            return await self.create_investment_trust(stock)
        elif self.is_japanese_stock(stock.symbol):
            return await self.create_japanese_stock(stock)
        elif self.is_us_stock(stock.symbol):
            return await self.create_us_stock(stock)
        else:
            raise ValueError("Invalid stock symbol format")

    def is_investment_trust(self, symbol: str) -> bool:
        return symbol.startswith("JP") and re.match(r"^JP[0-9A-Z]{10}$", symbol) is not None

    def is_japanese_stock(self, symbol: str) -> bool:
        return re.match(r"^[0-9]{4}$", symbol) is not None

    def is_us_stock(self, symbol: str) -> bool:
        return re.match(r"^[A-Z]{1,5}$", symbol) is not None

    async def create_investment_trust(self, stock: schemas.StockCreate) -> models.Stock:
        # 投資信託の詳細情報を取得
        details = await fetch_investment_trust_details(stock.symbol)
        name = details["name"]

        db_stock = models.Stock(
            symbol=stock.symbol,
            name=name,
            name_en="",
            market="JPX",
            security_type="FUND",
            currency="JPY",
        )
        self.db.add(db_stock)
        await self.db.commit()
        await self.db.refresh(db_stock)
        return db_stock

    async def create_japanese_stock(self, stock: schemas.StockCreate) -> models.Stock:
        company_info = jquants_client.get_company_info(stock.symbol)
        if not company_info:
            raise ValueError("Company information not found")

        db_stock = models.Stock(
            symbol=stock.symbol,
            name=company_info.get("CompanyName"),
            name_en=company_info.get("CompanyNameEnglish"),
            market="JPX",
            security_type="STOCK",
            currency="JPY",
        )
        self.db.add(db_stock)

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

    async def create_us_stock(self, stock: schemas.StockCreate) -> models.Stock:
        # Alpha Vantage APIを使用して米国株の詳細情報を取得
        data = await fetch_us_stock_overview(stock.symbol)

        if not data:
            # ETFの可能性があるため、SYMBOL_SEARCHを使用
            search_data = await fetch_us_stock_search(stock.symbol)
            if not search_data.get("bestMatches"):
                raise ValueError("Stock information not found")
            best_match = search_data.get("bestMatches", [])[0]
            name = best_match["2. name"].rstrip()  # 末尾のスペースを削除
            market = best_match["4. region"]
            security_type = "ETF"
        else:
            name = data["Name"]  # 銘柄名を取得
            market = data["Exchange"]  # 市場を取得
            industry = data.get("Sector", "")  # 産業を取得（存在しない場合は空文字）
            security_type = "STOCK"

        db_stock = models.Stock(
            symbol=stock.symbol,
            name=name,
            name_en=name,
            market=market,
            security_type=security_type,
            currency="USD",
        )
        self.db.add(db_stock)

        if security_type == "STOCK":
            db_stock_us_detail = models.StockUSDetail(
                symbol=stock.symbol,
                gics_sector=industry,
                gics_industry=industry,
                sp500_component=False,
                market=market,
            )
            self.db.add(db_stock_us_detail)

        await self.db.commit()
        await self.db.refresh(db_stock)
        return db_stock

    async def list_stocks(self, market: Optional[str] = None) -> List[models.Stock]:
        query = select(models.Stock)
        if market:
            query = query.where(models.Stock.market == market)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def delete_stock(self, symbol: str) -> bool:
        """
        指定されたシンボルの銘柄を削除する
        - symbol: 銘柄シンボル
        - 戻り値: 削除成功時はTrue、失敗時はFalse
        """
        query = select(models.Stock).where(models.Stock.symbol == symbol)
        result = await self.db.execute(query)
        db_stock = result.scalar_one_or_none()

        if not db_stock:
            return False

        # 関連する詳細情報テーブルの削除
        # 日本株の詳細情報を削除
        jpx_detail_query = select(models.StockJPXDetail).where(models.StockJPXDetail.symbol == symbol)
        jpx_detail_result = await self.db.execute(jpx_detail_query)
        if jpx_detail := jpx_detail_result.scalar_one_or_none():
            await self.db.delete(jpx_detail)

        # 米国株の詳細情報を削除
        us_detail_query = select(models.StockUSDetail).where(models.StockUSDetail.symbol == symbol)
        us_detail_result = await self.db.execute(us_detail_query)
        if us_detail := us_detail_result.scalar_one_or_none():
            await self.db.delete(us_detail)

        # 株式情報を削除
        await self.db.delete(db_stock)
        await self.db.commit()
        return True
