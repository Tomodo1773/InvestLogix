from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas


class TransactionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_transaction(self, transaction: schemas.TransactionCreate, user_id: int) -> Optional[models.Transaction]:
        # 株式の存在確認
        stock_query = select(models.Stock).where(models.Stock.symbol == transaction.symbol)
        stock_result = await self.db.execute(stock_query)
        stock = stock_result.scalar_one_or_none()

        if not stock:
            return None

        # 文字列をdatetimeに変換
        transaction_date = datetime.fromisoformat(transaction.transaction_date)

        # 取引情報の登録（transaction_dateを変換したものに置き換え）
        transaction_dict = transaction.model_dump()
        transaction_dict["transaction_date"] = transaction_date
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
            await self._handle_sell_transaction(holding, transaction)

        await self.db.commit()
        await self.db.refresh(db_transaction)
        return db_transaction

    async def _handle_buy_transaction(self, holding, transaction, user_id):
        if holding:
            # 既存の保有がある場合は更新
            new_quantity = holding.quantity + transaction.quantity
            new_total_cost = holding.total_cost + (transaction.quantity * transaction.price)
            holding.quantity = new_quantity
            holding.total_cost = new_total_cost
            holding.average_cost = new_total_cost / new_quantity
        else:
            # 新規保有の作成
            holding = models.Holding(
                user_id=user_id,
                symbol=transaction.symbol,
                quantity=transaction.quantity,
                average_cost=transaction.price,
                total_cost=transaction.quantity * transaction.price,
            )
            self.db.add(holding)

    async def _handle_sell_transaction(self, holding, transaction):
        holding.quantity -= transaction.quantity
        if holding.quantity == 0:
            await self.db.delete(holding)
        else:
            holding.total_cost = holding.average_cost * holding.quantity

    async def list_transactions(self, user_id: int) -> List[models.Transaction]:
        query = (
            select(models.Transaction)
            .where(models.Transaction.user_id == user_id)
            .order_by(models.Transaction.transaction_date.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()
