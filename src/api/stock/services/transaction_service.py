from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from .. import models, schemas
from .holding_service import (
    calculate_holding_from_transactions,
    update_single_holding_pl,
)
from .stock_service import StockService


class TransactionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.stock_service = StockService(db)

    async def create_transaction(self, transaction: schemas.TransactionCreate, user_id: int) -> Optional[models.Transaction]:
        # 株式の存在確認または登録
        stock_query = select(models.Stock).where(models.Stock.symbol == transaction.symbol)
        stock_result = await self.db.execute(stock_query)
        stock = stock_result.scalar_one_or_none()

        if not stock:
            stock = await self.stock_service.create_stock(schemas.StockCreate(symbol=transaction.symbol))

        # 取引情報の登録
        transaction_dict = transaction.model_dump()
        db_transaction = models.Transaction(**transaction_dict, user_id=user_id)
        self.db.add(db_transaction)

        # 保有情報の更新
        holding_query = select(models.Holding).where(
            models.Holding.user_id == user_id, models.Holding.symbol == transaction.symbol
        )
        holding_result = await self.db.execute(holding_query)
        holding = holding_result.scalar_one_or_none()

        if transaction.transaction_type == "buy":
            await self._handle_buy_transaction(holding, transaction, user_id)
        elif transaction.transaction_type == "sell":
            if not holding or holding.quantity < transaction.quantity:
                return None
            await self._handle_sell_transaction(holding, transaction, db_transaction)

        await self.db.commit()
        await self.db.refresh(db_transaction)

        # 取引登録後に保有損益を更新
        await update_single_holding_pl(self.db, user_id, transaction.symbol)

        return db_transaction

    async def _handle_buy_transaction(self, holding, transaction, user_id):
        # トランザクション履歴から最新の保有情報を計算
        new_quantity, new_average_cost, new_total_cost = await calculate_holding_from_transactions(
            self.db, user_id, transaction.symbol
        )

        if holding:
            # 既存の保有を更新
            holding.quantity = new_quantity
            holding.average_cost = new_average_cost
            holding.total_cost = new_total_cost
        else:
            # 新規保有の作成
            holding = models.Holding(
                user_id=user_id,
                symbol=transaction.symbol,
                quantity=new_quantity,
                average_cost=new_average_cost,
                total_cost=new_total_cost,
            )
            self.db.add(holding)

    async def _handle_sell_transaction(self, holding, transaction, db_transaction):
        # トランザクション履歴から最新の保有情報を計算
        new_quantity, new_average_cost, new_total_cost = await calculate_holding_from_transactions(
            self.db, holding.user_id, transaction.symbol
        )

        # 売却による実現損益の計算と保存
        realized_pl_for_sale = (transaction.price - holding.average_cost) * transaction.quantity
        # TransactionCreateオブジェクトではなく、DBモデルに実現損益を設定
        db_transaction.realized_pl = realized_pl_for_sale

        # 保有情報の更新
        holding.quantity = new_quantity
        holding.average_cost = new_average_cost
        holding.total_cost = new_total_cost

        # 実現損益の再計算
        realized_pl_query = select(func.sum(models.Transaction.realized_pl)).where(
            models.Transaction.user_id == holding.user_id,
            models.Transaction.symbol == holding.symbol,
            models.Transaction.transaction_type == "sell",
        )
        result = await self.db.execute(realized_pl_query)
        total_realized_pl = result.scalar() or Decimal("0")
        holding.realized_pl = total_realized_pl

    async def list_transactions(self, user_id: int) -> List[models.Transaction]:
        query = (
            select(models.Transaction, models.Stock.name)
            .join(models.Stock, models.Transaction.symbol == models.Stock.symbol)
            .where(models.Transaction.user_id == user_id)
            .order_by(models.Transaction.transaction_date.desc())
        )
        result = await self.db.execute(query)
        transactions = []
        for row in result:
            transaction = row[0]
            transaction.stock_name = row[1]
            transactions.append(transaction)
        return transactions
