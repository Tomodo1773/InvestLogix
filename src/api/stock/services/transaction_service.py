from decimal import Decimal
from typing import Dict, List, Optional, Union

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas
from .holding_service import (
    calculate_holding_from_transactions,
    calculate_realized_pl_from_transactions,
    list_holdings,
    update_single_holding_pl,
)
from .stock_service import StockService


class TransactionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.stock_service = StockService(db)

    async def create_transaction(
        self, transaction: schemas.TransactionCreate, user_id: int
    ) -> Optional[models.Transaction]:
        # 株式の存在確認または登録
        stock_query = select(models.Stock).where(models.Stock.symbol == transaction.symbol)
        stock_result = await self.db.execute(stock_query)
        stock = stock_result.scalar_one_or_none()

        if not stock:
            stock = await self.stock_service.create_stock(schemas.StockCreate(symbol=transaction.symbol))

        # 保有情報の取得
        holding_query = select(models.Holding).where(
            models.Holding.user_id == user_id, models.Holding.symbol == transaction.symbol
        )
        holding_result = await self.db.execute(holding_query)
        holding = holding_result.scalar_one_or_none()

        # 売却の場合は、トランザクションを登録する前に売却前の平均取得単価を取得
        average_cost_before_sell = None
        if transaction.transaction_type == "sell":
            if not holding:
                return None
            # 売却前に保有数量を再計算（調整済み値を反映）
            current_quantity, average_cost_before_sell, _ = await calculate_holding_from_transactions(
                self.db, user_id, transaction.symbol
            )
            if current_quantity < transaction.quantity:
                return None

        # 取引情報の登録
        transaction_dict = transaction.model_dump()
        db_transaction = models.Transaction(**transaction_dict, user_id=user_id)
        self.db.add(db_transaction)
        await self.db.flush()

        # 保有情報の更新
        if transaction.transaction_type == "buy":
            await self._handle_buy_transaction(holding, transaction, user_id)
        elif transaction.transaction_type == "sell":
            await self._handle_sell_transaction(
                holding, transaction, db_transaction, average_cost_before_sell
            )

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

    async def _handle_sell_transaction(self, holding, transaction, db_transaction, average_cost_before_sell):
        # 売却による実現損益の計算と保存（調整済み値ベースの平均取得単価を使用）
        # db_transactionを使用（TransactionCreateには調整済み値がないため）
        # Pythonのorで0もNone同様にフォールバック
        sell_price = db_transaction.adjusted_price or db_transaction.price
        sell_quantity = db_transaction.adjusted_quantity or db_transaction.quantity
        realized_pl_for_sale = (sell_price - average_cost_before_sell) * sell_quantity
        # TransactionCreateオブジェクトではなく、DBモデルに実現損益を設定
        db_transaction.realized_pl = realized_pl_for_sale

        # autoflush=False のため、集計前に最新の売却データをDBへ反映させる
        await self.db.flush()

        # 売却後の保有情報を計算（売却トランザクションを含む）
        new_quantity, new_average_cost, new_total_cost = await calculate_holding_from_transactions(
            self.db, holding.user_id, transaction.symbol
        )

        # 保有情報の更新
        holding.quantity = new_quantity
        holding.average_cost = new_average_cost
        holding.total_cost = new_total_cost

        # 実現損益の再計算
        holding.realized_pl = await calculate_realized_pl_from_transactions(
            self.db, holding.user_id, holding.symbol
        )

    async def list_transactions(
        self, user_id: int, symbol: Optional[str] = None, include_unrealized_pl: bool = False
    ) -> Union[List[models.Transaction], List[schemas.TransactionWithPL]]:
        # 銘柄名を取得するためにStockテーブルを結合
        query = (
            select(models.Transaction, models.Stock.name)
            .join(models.Stock, models.Transaction.symbol == models.Stock.symbol)
            .where(models.Transaction.user_id == user_id)
        )

        # シンボルが指定されている場合は、フィルタリングを追加
        if symbol:
            query = query.where(models.Transaction.symbol == symbol)

        query = query.order_by(models.Transaction.transaction_date.desc())
        result = await self.db.execute(query)
        transactions = []
        for row in result:
            transaction = row[0]
            transaction.stock_name = row[1]
            transactions.append(transaction)

        # 未実現損益を含める場合
        if include_unrealized_pl and symbol:
            # holdingから現在価格を取得
            holdings = await list_holdings(self.db, user_id, symbol)
            current_price = holdings[0].current_price if holdings and holdings[0].current_price else None

            # 各買付取引に対して損益を計算
            transactions_with_pl = []
            for transaction in transactions:
                transaction_dict = {
                    "transaction_id": transaction.transaction_id,
                    "user_id": transaction.user_id,
                    "symbol": transaction.symbol,
                    "transaction_type": transaction.transaction_type,
                    "quantity": transaction.quantity,
                    "price": transaction.price,
                    "usd_price": transaction.usd_price,
                    "adjusted_price": transaction.adjusted_price,
                    "account_type": transaction.account_type,
                    "fee": transaction.fee,
                    "tax": transaction.tax,
                    "realized_pl": transaction.realized_pl,
                    "transaction_date": transaction.transaction_date,
                    "stock_name": transaction.stock_name,
                    "unrealized_pl": None,
                    "unrealized_pl_percentage": None,
                }

                # 買付取引の場合のみ損益を計算
                if transaction.transaction_type == "buy" and current_price:
                    cost = transaction.price * transaction.quantity
                    market_value = current_price * transaction.quantity
                    unrealized_pl = market_value - cost
                    unrealized_pl_percentage = (unrealized_pl / cost * 100) if cost > 0 else Decimal("0")
                    transaction_dict["unrealized_pl"] = unrealized_pl
                    transaction_dict["unrealized_pl_percentage"] = unrealized_pl_percentage

                transactions_with_pl.append(schemas.TransactionWithPL(**transaction_dict))

            return transactions_with_pl

        return transactions

    async def get_monthly_summary(self, user_id: int) -> List[Dict]:
        """
        ユーザーの月次トランザクション集計を取得する

        Returns:
            List[Dict]: 年月ごとの口座種別別購入金額集計
        """
        # 購入取引（transaction_type='buy'）のみを対象に集計
        # transaction_date を JST に変換して月ごとに集計するクエリ
        transaction_date_jst = models.Transaction.transaction_date.op("AT TIME ZONE")("Asia/Tokyo")
        year = extract("year", transaction_date_jst).label("year")
        month = extract("month", transaction_date_jst).label("month")

        query = (
            select(
                year,
                month,
                models.Transaction.account_type,
                func.sum(models.Transaction.price * models.Transaction.quantity).label("total_amount"),
            )
            .where(models.Transaction.user_id == user_id, models.Transaction.transaction_type == "buy")
            .group_by(
                year,
                month,
                models.Transaction.account_type,
            )
            .order_by("year", "month", models.Transaction.account_type)
        )

        result = await self.db.execute(query)
        raw_data = result.all()

        # 集計結果をまとめる
        summary = {}
        for row in raw_data:
            year = int(row.year)
            month = int(row.month)
            account_type = row.account_type
            amount = float(row.total_amount)

            # アカウント名をAPIレスポンス用に変換
            account_name = self._convert_account_type_name(account_type)

            key = (year, month)
            if key not in summary:
                summary[key] = {
                    "year": year,
                    "month": month,
                    "total_purchase": {
                        "juniorNISA": 0.0,
                        "oldNISA": 0.0,
                        "NISAAccumulation": 0.0,
                        "NISAGrowth": 0.0,
                        "specific": 0.0,
                    },
                }

            summary[key]["total_purchase"][account_name] = amount

        # 日付順にソートして返す
        return [summary[key] for key in sorted(summary.keys())]

    async def get_yearly_summary(self, user_id: int) -> List[Dict]:
        """
        ユーザーの年次トランザクション集計を取得する

        Returns:
            List[Dict]: 年ごとの口座種別別購入金額集計
        """
        # 購入取引（transaction_type='buy'）のみを対象に集計
        # transaction_date を JST に変換して年ごとに集計するクエリ
        transaction_date_jst = models.Transaction.transaction_date.op("AT TIME ZONE")("Asia/Tokyo")
        year = extract("year", transaction_date_jst).label("year")

        query = (
            select(
                year,
                models.Transaction.account_type,
                func.sum(models.Transaction.price * models.Transaction.quantity).label("total_amount"),
            )
            .where(models.Transaction.user_id == user_id, models.Transaction.transaction_type == "buy")
            .group_by(
                year,
                models.Transaction.account_type,
            )
            .order_by("year", models.Transaction.account_type)
        )

        result = await self.db.execute(query)
        raw_data = result.all()

        # 集計結果をまとめる
        summary = {}
        for row in raw_data:
            year = int(row.year)
            account_type = row.account_type
            amount = float(row.total_amount)

            # アカウント名をAPIレスポンス用に変換
            account_name = self._convert_account_type_name(account_type)

            if year not in summary:
                summary[year] = {
                    "year": year,
                    "total_purchase": {
                        "juniorNISA": 0.0,
                        "oldNISA": 0.0,
                        "NISAAccumulation": 0.0,
                        "NISAGrowth": 0.0,
                        "specific": 0.0,
                    },
                }

            summary[year]["total_purchase"][account_name] = amount

        # 年順にソートして返す
        return [summary[year] for year in sorted(summary.keys())]

    def _convert_account_type_name(self, account_type: str) -> str:
        """アカウント種別名をAPIレスポンス用に変換する"""
        mapping = {
            "ジュニアNISA": "juniorNISA",
            "旧NISA": "oldNISA",
            "NISA(つみたて投資枠)": "NISAAccumulation",
            "NISA(成長投資枠)": "NISAGrowth",
            "特定": "specific",
        }
        return mapping.get(account_type, account_type)
