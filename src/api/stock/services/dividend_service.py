from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from .. import models, schemas
from ..utils import get_jst_extract_columns
from .holding_service import update_single_holding_pl
from .stock_service import StockService


class DividendService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.stock_service = StockService(db)

    async def create_dividend(
        self, dividend: schemas.DividendCreate, user_id: int
    ) -> Optional[models.Dividend]:
        # 株式の存在確認または登録
        await self.stock_service.get_or_create_stock(dividend.symbol, user_id)

        # 配当情報の登録
        db_dividend = models.Dividend(**dividend.model_dump(), user_id=user_id)
        self.db.add(db_dividend)
        await self.db.flush()

        # Holdingsテーブルのtotal_dividendを更新
        holdings_query = select(models.Holding).where(
            models.Holding.user_id == user_id, models.Holding.symbol == dividend.symbol
        )
        holdings_result = await self.db.execute(holdings_query)
        holding = holdings_result.scalar_one_or_none()
        logger.info(
            "Holdingsを取得しました action=select user_id={} symbol={} found={}",
            user_id,
            dividend.symbol,
            bool(holding),
        )

        if holding:
            # total_dividend に配当の純額（税・手数料控除後）を加算
            net_dividend = float(dividend.total_amount)
            if dividend.tax is not None:
                net_dividend -= float(dividend.tax)
            if dividend.fee is not None:
                net_dividend -= float(dividend.fee)

            holding.total_dividend = (holding.total_dividend or 0.0) + net_dividend
            # 注: unrealized_pl等の損益計算はupdate_single_holding_plに一元化

        await self.db.flush()
        await self.db.refresh(db_dividend)

        # 配当登録後に保有損益を更新
        await update_single_holding_pl(self.db, user_id, dividend.symbol)

        logger.info(
            "Dividendに登録しました action=commit user_id={} symbol={} dividend_id={} total_amount={} payment_date={}",
            user_id,
            dividend.symbol,
            db_dividend.dividend_id,
            dividend.total_amount,
            dividend.payment_date,
        )

        return db_dividend

    async def list_dividends(self, user_id: int, symbol: Optional[str] = None) -> List[models.Dividend]:
        query = (
            select(models.Dividend, models.Stock.name)
            .join(models.Stock, models.Dividend.symbol == models.Stock.symbol)
            .where(models.Dividend.user_id == user_id)
        )

        # シンボルが指定されている場合は、フィルタリングを追加
        if symbol:
            query = query.where(models.Dividend.symbol == symbol)

        query = query.order_by(models.Dividend.payment_date.desc())
        result = await self.db.execute(query)
        dividends = []
        for row in result:
            dividend = row[0]
            dividend.stock_name = row[1]
            dividends.append(dividend)
        logger.info(
            "Dividendを取得しました action=select user_id={} symbol={} count={}",
            user_id,
            symbol,
            len(dividends),
        )
        return dividends

    async def get_monthly_dividends(self, user_id: int) -> List[dict]:
        """月次の配当金集計を取得する

        Args:
            user_id: ユーザーID

        Returns:
            List[dict]: 月ごとの配当金集計のリスト（年月と配当金額）
        """
        # payment_date を JST に変換して月ごとに配当金を集計するクエリ
        # ※ payment_date は DB では UTC で保存されているため、JST への変換が必要
        year, month = get_jst_extract_columns(models.Dividend.payment_date)

        query = (
            select(
                year,
                month,
                func.sum(
                    models.Dividend.total_amount
                    - func.coalesce(models.Dividend.tax, 0)
                    - func.coalesce(models.Dividend.fee, 0)
                ).label("total_dividend"),
            )
            .where(models.Dividend.user_id == user_id)
            .group_by(year, month)
            .order_by(year, month)
        )

        result = await self.db.execute(query)

        # クエリ結果を (year, month) -> total_dividend のマップに変換
        dividend_map: dict[tuple[int, int], float] = {}
        for row in result:
            dividend_map[(int(row.year), int(row.month))] = float(row.total_dividend)

        if not dividend_map:
            return []

        # 最初の月から最後の月まで全月を生成し、データがない月は 0.0 で補完
        # クエリが ORDER BY year, month で返すため、dict の挿入順序で先頭/末尾を取得
        keys = list(dividend_map.keys())
        start_year, start_month = keys[0]
        end_year, end_month = keys[-1]

        monthly_dividends: list[dict] = []
        year, month = start_year, start_month
        while (year, month) <= (end_year, end_month):
            monthly_dividends.append(
                {
                    "year": year,
                    "month": month,
                    "total_dividend": dividend_map.get((year, month), 0.0),
                }
            )
            if month == 12:
                year += 1
                month = 1
            else:
                month += 1

        logger.info("月次配当集計を取得しました user_id={} months={}", user_id, len(monthly_dividends))

        return monthly_dividends

    async def get_dividends_by_symbol(
        self, user_id: int, year: int | None = None, month: int | None = None
    ) -> List[dict]:
        """銘柄別の配当金集計を取得する（税・手数料控除後の純額、金額降順）

        Args:
            user_id: ユーザーID
            year: フィルタする年（JSTベース）。month と併用必須。省略時は通算
            month: フィルタする月（JSTベース）。year と併用必須。省略時は通算

        Returns:
            List[dict]: 銘柄ごとの配当金集計のリスト（銘柄コード・銘柄名・配当金額）
        """
        total_dividend = func.sum(
            models.Dividend.total_amount
            - func.coalesce(models.Dividend.tax, 0)
            - func.coalesce(models.Dividend.fee, 0)
        ).label("total_dividend")

        query = (
            select(
                models.Dividend.symbol,
                models.Stock.name.label("stock_name"),
                total_dividend,
            )
            .join(models.Stock, models.Dividend.symbol == models.Stock.symbol)
            .where(models.Dividend.user_id == user_id)
        )

        if year is not None and month is not None:
            year_col, month_col = get_jst_extract_columns(models.Dividend.payment_date)
            query = query.where(year_col == year, month_col == month)

        query = query.group_by(models.Dividend.symbol, models.Stock.name).order_by(total_dividend.desc())

        result = await self.db.execute(query)
        dividends_by_symbol = [
            {
                "symbol": row.symbol,
                "stock_name": row.stock_name,
                "total_dividend": float(row.total_dividend),
            }
            for row in result
        ]

        logger.info("銘柄別配当集計を取得しました user_id={} symbols={}", user_id, len(dividends_by_symbol))

        return dividends_by_symbol
