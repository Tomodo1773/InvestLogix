from typing import List, Optional

from loguru import logger
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
            user_id: ユーザーID

        Returns:
            登録された株式分割情報
        """
        # 株式分割情報を登録
        db_split = models.StockSplit(
            user_id=user_id,
            symbol=split_data.symbol,
            split_date=split_data.split_date,
            split_ratio=split_data.split_ratio,
        )
        self.db.add(db_split)
        await self.db.flush()

        # 調整値を再計算（ユーザーの取引のみ対象）
        await self.recalculate_adjusted_values(split_data.symbol, user_id)

        await self.db.commit()
        await self.db.refresh(db_split)
        logger.info(
            "StockSplitを登録しました action=create user_id={} symbol={} split_id={}",
            user_id,
            split_data.symbol,
            db_split.split_id,
        )
        return db_split

    async def list_stock_splits(self, user_id: int, symbol: Optional[str] = None) -> List[models.StockSplit]:
        """
        株式分割履歴を取得する

        Args:
            user_id: ユーザーID
            symbol: 銘柄コード（指定時は該当銘柄のみ、未指定時は全銘柄）

        Returns:
            株式分割履歴のリスト
        """
        query = (
            select(models.StockSplit, models.Stock.name)
            .join(models.Stock, models.StockSplit.symbol == models.Stock.symbol)
            .where(models.StockSplit.user_id == user_id)
            .order_by(models.StockSplit.split_date.desc())
        )

        if symbol:
            query = query.where(models.StockSplit.symbol == symbol)

        result = await self.db.execute(query)
        splits = []
        for row in result:
            stock_split = row[0]
            stock_split.stock_name = row[1]
            splits.append(stock_split)
        logger.info(
            "StockSplitを取得しました action=select user_id={} symbol={} count={}",
            user_id,
            symbol or "all",
            len(splits),
        )
        return splits

    async def delete_stock_split(self, split_id: int, user_id: int) -> bool:
        """
        株式分割情報を削除し、調整値を再計算する

        Args:
            split_id: 削除する株式分割ID
            user_id: ユーザーID

        Returns:
            削除成功時True、分割情報が見つからない場合False
        """
        # 分割情報を取得（ユーザーIDでフィルタリング）
        result = await self.db.execute(
            select(models.StockSplit).where(
                models.StockSplit.split_id == split_id,
                models.StockSplit.user_id == user_id,
            )
        )
        split = result.scalar_one_or_none()

        if not split:
            logger.info(
                "StockSplitが見つかりませんでした action=select user_id={} split_id={} found=false",
                user_id,
                split_id,
            )
            return False

        symbol = split.symbol

        # 分割情報を削除
        await self.db.delete(split)
        await self.db.flush()

        # 調整値を再計算（ユーザーの取引のみ対象）
        await self.recalculate_adjusted_values(symbol, user_id)

        await self.db.commit()
        logger.info(
            "StockSplitを削除しました action=delete user_id={} symbol={} split_id={}",
            user_id,
            symbol,
            split_id,
        )
        return True

    async def recalculate_adjusted_values(self, symbol: str, user_id: int) -> None:
        """
        指定銘柄のユーザー取引の調整値を再計算する（冪等性保証）

        計算ロジック:
        1. 該当銘柄・ユーザーの全分割情報を取得（split_date順）
        2. 該当銘柄・ユーザーの全取引を取得
        3. 各取引に対して:
           - 取引日より後の分割を全て適用
           - adjusted_quantity = quantity * (split_ratio1 * split_ratio2 * ...)
           - adjusted_price = price / (split_ratio1 * split_ratio2 * ...)

        Args:
            symbol: 銘柄コード
            user_id: ユーザーID
        """
        # 分割情報を日付順で取得（ユーザーIDでフィルタリング）
        splits_result = await self.db.execute(
            select(models.StockSplit)
            .where(
                models.StockSplit.symbol == symbol,
                models.StockSplit.user_id == user_id,
            )
            .order_by(models.StockSplit.split_date.asc())
        )
        splits = list(splits_result.scalars().all())

        # 分割情報がない場合は調整値をNULLに設定
        if not splits:
            transactions_result = await self.db.execute(
                select(models.Transaction).where(
                    models.Transaction.symbol == symbol,
                    models.Transaction.user_id == user_id,
                )
            )
            transactions = list(transactions_result.scalars().all())

            for transaction in transactions:
                transaction.adjusted_quantity = None
                transaction.adjusted_price = None

            await self.db.flush()
            logger.info(
                "Transactionを更新しました action=bulk_update user_id={} symbol={} count={} reason=no_splits",
                user_id,
                symbol,
                len(transactions),
            )
            return

        # ユーザーの全取引を取得
        transactions_result = await self.db.execute(
            select(models.Transaction).where(
                models.Transaction.symbol == symbol,
                models.Transaction.user_id == user_id,
            )
        )
        transactions = list(transactions_result.scalars().all())

        # 各取引の調整値を計算
        for transaction in transactions:
            cumulative_ratio = 1.0

            # 取引日より後の分割を全て適用
            for split in splits:
                if transaction.transaction_date < split.split_date:
                    cumulative_ratio *= split.split_ratio

            # 調整値を設定
            if cumulative_ratio != 1.0:
                transaction.adjusted_quantity = transaction.quantity * cumulative_ratio
                transaction.adjusted_price = transaction.price / cumulative_ratio
            else:
                # 分割の影響を受けない場合はNULL
                transaction.adjusted_quantity = None
                transaction.adjusted_price = None

        await self.db.flush()
        logger.info(
            "Transactionを更新しました action=bulk_update user_id={} symbol={} count={} split_count={}",
            user_id,
            symbol,
            len(transactions),
            len(splits),
        )
