from decimal import Decimal
from typing import List, Optional

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas
from .holding_service import update_single_holding_pl
from .stock_service import StockService


class DividendService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.stock_service = StockService(db)

    async def create_dividend(self, dividend: schemas.DividendCreate, user_id: int) -> Optional[models.Dividend]:
        # 株式の存在確認または登録
        stock_query = select(models.Stock).where(models.Stock.symbol == dividend.symbol)
        stock_result = await self.db.execute(stock_query)
        stock = stock_result.scalar_one_or_none()

        if not stock:
            stock = await self.stock_service.create_stock(schemas.StockCreate(symbol=dividend.symbol))

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

        if holding:
            # total_dividend に配当の純額（税・手数料控除後）を加算
            net_dividend = Decimal(dividend.total_amount)
            if dividend.tax is not None:
                net_dividend -= Decimal(dividend.tax)
            if dividend.fee is not None:
                net_dividend -= Decimal(dividend.fee)

            holding.total_dividend = (holding.total_dividend or Decimal("0")) + net_dividend
            # 未実現損益の更新
            if holding.market_value is not None:
                holding.unrealized_pl = (
                    holding.market_value + (holding.realized_pl or Decimal("0")) + holding.total_dividend - holding.total_cost
                )
                if holding.total_cost > 0:
                    holding.unrealized_pl_percentage = (holding.unrealized_pl / holding.total_cost) * 100

        await self.db.commit()
        await self.db.refresh(db_dividend)

        # 配当登録後に保有損益を更新
        await update_single_holding_pl(self.db, user_id, dividend.symbol)

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
        return dividends

    async def get_monthly_dividends(self, user_id: int) -> List[dict]:
        """月次の配当金集計を取得する

        Args:
            user_id: ユーザーID

        Returns:
            List[dict]: 月ごとの配当金集計のリスト（年月と配当金額）
        """
        # 月ごとに配当金を集計するクエリ
        query = (
            select(
                extract("year", models.Dividend.payment_date).label("year"),
                extract("month", models.Dividend.payment_date).label("month"),
                func.sum(
                    models.Dividend.total_amount
                    - func.coalesce(models.Dividend.tax, 0)
                    - func.coalesce(models.Dividend.fee, 0)
                ).label("total_dividend"),
            )
            .where(models.Dividend.user_id == user_id)
            .group_by(extract("year", models.Dividend.payment_date), extract("month", models.Dividend.payment_date))
            .order_by(extract("year", models.Dividend.payment_date), extract("month", models.Dividend.payment_date))
        )

        result = await self.db.execute(query)

        # 結果をディクショナリのリストとして返す
        monthly_dividends = []
        for row in result:
            monthly_dividends.append(
                {"year": int(row.year), "month": int(row.month), "total_dividend": float(row.total_dividend)}
            )

        return monthly_dividends
