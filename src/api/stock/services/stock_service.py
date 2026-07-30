import asyncio
import re
from typing import List, Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas
from .alphavantage_service import fetch_us_stock_overview, fetch_us_stock_search
from .classification_service import classify_fund_currency
from .errors import StockNotFoundError
from .investment_trust_service import fetch_investment_trust_details
from .jquants_service import get_jquants_client


class StockService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_stock(self, symbol: str, user_id: Optional[int] = None) -> models.Stock:
        """
        Stockを取得または作成する
        - 既存の場合: 登録済みのStockを返す
        - 未登録の場合: 新規作成して返す
        """
        query = select(models.Stock).where(models.Stock.symbol == symbol)
        result = await self.db.execute(query)
        stock = result.scalar_one_or_none()

        user_info = f"user_id={user_id} " if user_id is not None else ""
        logger.info(
            "Stockを取得しました action=select {}symbol={} found={}",
            user_info,
            symbol,
            bool(stock),
        )

        if not stock:
            stock = await self.create_stock(schemas.StockCreate(symbol=symbol))
            logger.info("Stockに登録しました action=create {}symbol={}", user_info, symbol)

        return stock

    async def create_stock(self, stock: schemas.StockCreate) -> models.Stock:
        """
        新規銘柄を登録する
        - すでに登録済みの場合は、登録済みの銘柄情報を返す
        - 新規の場合は、銘柄情報を登録して返す
        - 銘柄情報が取得できない場合はStockNotFoundErrorを発生させる
        """
        query = select(models.Stock).where(models.Stock.symbol == stock.symbol)
        result = await self.db.execute(query)
        db_stock = result.scalar_one_or_none()

        if db_stock:
            logger.info("Stockを取得しました action=select symbol={} found=true", stock.symbol)
            return db_stock  # 既に登録されている場合はそのまま返す

        try:
            logger.info("Stockが見つかりませんでした action=select symbol={} found=false", stock.symbol)
            if self.is_investment_trust(stock.symbol):
                return await self.create_investment_trust(stock)
            elif self.is_japanese_stock(stock.symbol):
                return await self.create_japanese_stock(stock)
            elif self.is_us_stock(stock.symbol):
                return await self.create_us_stock(stock)
            else:
                raise StockNotFoundError(f"Invalid stock symbol format: {stock.symbol}")
        except StockNotFoundError as e:
            logger.error("Stockの作成に失敗しました action=create symbol={} error={}", stock.symbol, str(e))
            raise
        except Exception as e:
            logger.error("Stockの作成に失敗しました action=create symbol={} error={}", stock.symbol, str(e))
            raise StockNotFoundError(f"Failed to get stock information: {stock.symbol}") from e

    def is_investment_trust(self, symbol: str) -> bool:
        return symbol.startswith("JP") and re.match(r"^JP[0-9A-Z]{10}$", symbol) is not None

    def is_japanese_stock(self, symbol: str) -> bool:
        return re.match(r"^[0-9]{4}$", symbol) is not None

    def is_us_stock(self, symbol: str) -> bool:
        return re.match(r"^[A-Z]{1,5}$", symbol) is not None

    async def _create_and_persist(self, symbol: str, defaults: dict, fetch_fn) -> models.Stock:
        """Stock新規作成の共通処理: モデル生成 → 外部API取得 → DB永続化"""
        db_stock = models.Stock(symbol=symbol, name="", name_en="", **defaults)
        self.db.add(db_stock)
        await fetch_fn(db_stock)
        await self.db.flush()
        await self.db.refresh(db_stock)
        return db_stock

    async def create_investment_trust(self, stock: schemas.StockCreate) -> models.Stock:
        db_stock = await self._create_and_persist(
            stock.symbol,
            {"market": "JPX", "security_type": "FUND", "currency": "JPY"},
            self._fetch_investment_trust_attrs,
        )
        logger.info("Stockを登録しました action=create symbol={} security_type=FUND", db_stock.symbol)
        return db_stock

    async def _fetch_investment_trust_attrs(self, db_stock: models.Stock) -> None:
        """外部APIから投資信託の属性を取得してdb_stockに反映する"""
        details = await fetch_investment_trust_details(db_stock.symbol)
        db_stock.name = details["name"]
        db_stock.currency = await classify_fund_currency(db_stock.name)

    async def create_japanese_stock(self, stock: schemas.StockCreate) -> models.Stock:
        db_stock = await self._create_and_persist(
            stock.symbol,
            {"market": "JPX", "security_type": "STOCK", "currency": "JPY"},
            self._fetch_japanese_stock_attrs,
        )
        logger.info(
            "Stockを登録しました action=create symbol={} security_type=STOCK market=JPX", stock.symbol
        )
        return db_stock

    async def _fetch_japanese_stock_attrs(self, db_stock: models.Stock) -> None:
        """外部APIから日本株の属性を取得してdb_stockに反映する"""
        company_info = get_jquants_client().get_company_info(db_stock.symbol)
        if not company_info:
            logger.error("企業情報が取得できませんでした action=external_io symbol={}", db_stock.symbol)
            raise StockNotFoundError(f"Company information not found for symbol: {db_stock.symbol}")

        db_stock.name = company_info.get("CoName")
        db_stock.name_en = company_info.get("CoNameEn")

        # JPX詳細情報の更新または作成
        jpx_query = select(models.StockJPXDetail).where(models.StockJPXDetail.symbol == db_stock.symbol)
        result = await self.db.execute(jpx_query)
        db_detail = result.scalar_one_or_none()
        if not db_detail:
            db_detail = models.StockJPXDetail(symbol=db_stock.symbol)
            self.db.add(db_detail)

        db_detail.sector_17_code = company_info.get("S17")
        db_detail.sector_17_name = company_info.get("S17Nm")
        db_detail.sector_33_code = company_info.get("S33")
        db_detail.sector_33_name = company_info.get("S33Nm")
        db_detail.market_segment = company_info.get("MktNm")
        db_detail.market_code = company_info.get("ScaleCat")
        db_detail.market_name = company_info.get("MktNm")
        db_detail.margin_trading = company_info.get("MarginCode") == "1"

    async def create_us_stock(self, stock: schemas.StockCreate) -> models.Stock:
        db_stock = await self._create_and_persist(
            stock.symbol,
            {"market": "", "security_type": "STOCK", "currency": "USD"},
            self._fetch_us_stock_attrs,
        )
        logger.info(
            "Stockを登録しました action=create symbol={} security_type={} market={}",
            stock.symbol,
            db_stock.security_type,
            db_stock.market,
        )
        return db_stock

    async def _fetch_us_stock_attrs(self, db_stock: models.Stock) -> None:
        """外部APIから米国株の属性を取得してdb_stockに反映する"""
        data = await fetch_us_stock_overview(db_stock.symbol)

        if not data:
            await asyncio.sleep(1.2)  # Alpha Vantage無料枠: 1リクエスト/秒制限の回避
            search_data = await fetch_us_stock_search(db_stock.symbol)
            if not search_data.get("bestMatches"):
                logger.error("Stock情報が見つかりませんでした action=external_io symbol={}", db_stock.symbol)
                raise StockNotFoundError(f"Stock information not found for symbol: {db_stock.symbol}")
            best_match = search_data["bestMatches"][0]
            name = best_match["2. name"].rstrip()
            market = best_match["4. region"]
            security_type = "ETF"
            industry = ""
        else:
            name = data["Name"]
            market = data["Exchange"]
            industry = data.get("Sector", "")
            security_type = "STOCK"

        db_stock.name = name
        db_stock.name_en = name
        db_stock.market = market
        db_stock.security_type = security_type

        # US詳細情報の更新または作成（STOCKの場合のみ）
        if security_type == "STOCK":
            us_query = select(models.StockUSDetail).where(models.StockUSDetail.symbol == db_stock.symbol)
            result = await self.db.execute(us_query)
            db_detail = result.scalar_one_or_none()
            if not db_detail:
                db_detail = models.StockUSDetail(symbol=db_stock.symbol)
                self.db.add(db_detail)

            db_detail.gics_sector = industry
            db_detail.gics_industry = industry
            db_detail.sp500_component = False
            db_detail.market = market

    async def refresh_stock(self, symbol: str) -> models.Stock:
        """既存銘柄の情報を外部APIから再取得して更新する"""
        query = select(models.Stock).where(models.Stock.symbol == symbol)
        result = await self.db.execute(query)
        db_stock = result.scalar_one_or_none()

        if not db_stock:
            raise StockNotFoundError(f"Stock not found: {symbol}")

        if self.is_investment_trust(symbol):
            await self._fetch_investment_trust_attrs(db_stock)
        elif self.is_japanese_stock(symbol):
            await self._fetch_japanese_stock_attrs(db_stock)
        elif self.is_us_stock(symbol):
            await self._fetch_us_stock_attrs(db_stock)
        else:
            raise StockNotFoundError(f"Invalid stock symbol format: {symbol}")

        await self.db.flush()
        await self.db.refresh(db_stock)
        logger.info("Stockを更新しました action=update symbol={}", symbol)
        return db_stock

    async def list_stocks(self, market: Optional[str] = None) -> List[models.Stock]:
        query = select(models.Stock)
        if market:
            query = query.where(models.Stock.market == market)
        result = await self.db.execute(query)
        stocks = result.scalars().all()
        logger.info("Stockを取得しました action=select market={} count={}", market or "all", len(stocks))
        return stocks

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
            logger.info("Stockが見つかりませんでした action=select symbol={} found=false", symbol)
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
        await self.db.flush()
        logger.info("Stockを削除しました action=delete symbol={}", symbol)
        return True
