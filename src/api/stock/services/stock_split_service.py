from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas


class StockSplitService:
    """株式分割情報の管理サービス"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_stock_split(
        self, split_data: schemas.StockSplitCreate, user_id: int
    ) -> models.StockSplit:
        """
        株式分割情報を登録し、過去取引の調整値を再計算する

        Args:
            split_data: 株式分割情報
            user_id: ユーザーID（認証用、現在は未使用）

        Returns:
            登録された株式分割情報
        """
        # 株式分割情報を登録
        db_split = models.StockSplit(
            symbol=split_data.symbol,
            split_date=split_data.split_date,
            split_ratio=split_data.split_ratio,
        )
        self.db.add(db_split)
        await self.db.flush()

        # 調整値を再計算
        await self.recalculate_adjusted_values(split_data.symbol)

        await self.db.commit()
        await self.db.refresh(db_split)
        return db_split

    async def list_stock_splits(self, symbol: Optional[str] = None) -> List[models.StockSplit]:
        """
        株式分割履歴を取得する

        Args:
            symbol: 銘柄コード（指定時は該当銘柄のみ、未指定時は全銘柄）

        Returns:
            株式分割履歴のリスト
        """
        query = select(models.StockSplit).order_by(models.StockSplit.split_date.desc())

        if symbol:
            query = query.where(models.StockSplit.symbol == symbol)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete_stock_split(self, split_id: int) -> bool:
        """
        株式分割情報を削除し、調整値を再計算する

        Args:
            split_id: 削除する株式分割ID

        Returns:
            削除成功時True、分割情報が見つからない場合False
        """
        # 分割情報を取得
        result = await self.db.execute(
            select(models.StockSplit).where(models.StockSplit.split_id == split_id)
        )
        split = result.scalar_one_or_none()

        if not split:
            return False

        symbol = split.symbol

        # 分割情報を削除
        await self.db.delete(split)
        await self.db.flush()

        # 調整値を再計算
        await self.recalculate_adjusted_values(symbol)

        await self.db.commit()
        return True

    async def recalculate_adjusted_values(self, symbol: str) -> None:
        """
        指定銘柄の全取引の調整値を再計算する（冪等性保証）

        計算ロジック:
        1. 該当銘柄の全分割情報を取得（split_date順）
        2. 該当銘柄の全取引を取得
        3. 各取引に対して:
           - 取引日より後の分割を全て適用
           - adjusted_quantity = quantity * (split_ratio1 * split_ratio2 * ...)
           - adjusted_price = price / (split_ratio1 * split_ratio2 * ...)

        Args:
            symbol: 銘柄コード
        """
        # 分割情報を日付順で取得
        splits_result = await self.db.execute(
            select(models.StockSplit)
            .where(models.StockSplit.symbol == symbol)
            .order_by(models.StockSplit.split_date.asc())
        )
        splits = list(splits_result.scalars().all())

        # 分割情報がない場合は調整値をNULLに設定
        if not splits:
            transactions_result = await self.db.execute(
                select(models.Transaction).where(models.Transaction.symbol == symbol)
            )
            transactions = list(transactions_result.scalars().all())

            for transaction in transactions:
                transaction.adjusted_quantity = None
                transaction.adjusted_price = None

            await self.db.flush()
            return

        # 全取引を取得
        transactions_result = await self.db.execute(
            select(models.Transaction).where(models.Transaction.symbol == symbol)
        )
        transactions = list(transactions_result.scalars().all())

        # 各取引の調整値を計算
        for transaction in transactions:
            cumulative_ratio = Decimal("1.0")

            # 取引日より後の分割を全て適用
            for split in splits:
                if transaction.transaction_date < split.split_date:
                    cumulative_ratio *= split.split_ratio

            # 調整値を設定
            if cumulative_ratio != Decimal("1.0"):
                transaction.adjusted_quantity = transaction.quantity * cumulative_ratio
                transaction.adjusted_price = transaction.price / cumulative_ratio
            else:
                # 分割の影響を受けない場合はNULL
                transaction.adjusted_quantity = None
                transaction.adjusted_price = None

        await self.db.flush()
