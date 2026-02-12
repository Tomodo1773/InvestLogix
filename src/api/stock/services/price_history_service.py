"""
株価時系列データ取得サービス
日本株はJ-Quants API、米国株はStooqを使用
"""

from datetime import datetime, timedelta
from typing import List

import pandas as pd
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Stock
from ..schemas import PriceDataPoint, PriceHistoryInterval
from ..utils.cache import timed_cache
from .jquants_service import get_jquants_client
from .stooq_service import fetch_us_daily_prices_from_stooq


class PriceHistoryService:
    """株価時系列データ取得サービス"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _calculate_start_date(interval: PriceHistoryInterval, limit: int) -> str:
        """間隔と取得件数から開始日を計算する（十分な余裕を持たせる）"""
        today = datetime.now()
        if interval == PriceHistoryInterval.DAILY:
            # 平日営業日を考慮して、limit * 1.5日分遡る
            days_back = int(limit * 1.5)
        elif interval == PriceHistoryInterval.WEEKLY:
            # 週足なら limit週 * 7日
            days_back = limit * 7
        else:  # MONTHLY
            # 月足なら limit月 * 31日（ただし最大5年=1825日まで）
            days_back = min(limit * 31, 1825)
        start = today - timedelta(days=days_back)
        return start.strftime("%Y-%m-%d")

    @staticmethod
    def _aggregate_to_weekly(data: List[dict]) -> List[dict]:
        """日次データを週次データに集計"""
        if not data:
            return []

        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        # 週次でリサンプリング（月曜始まり）
        weekly = df.resample("W-MON").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
        )

        # NaNを削除してリストに変換
        weekly = weekly.dropna()
        result = []
        for date, row in weekly.iterrows():
            result.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": int(row["volume"]),
                }
            )
        return result

    @staticmethod
    def _aggregate_to_monthly(data: List[dict]) -> List[dict]:
        """日次データを月次データに集計"""
        if not data:
            return []

        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        # 月次でリサンプリング
        monthly = df.resample("MS").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
        )

        # NaNを削除してリストに変換
        monthly = monthly.dropna()
        result = []
        for date, row in monthly.iterrows():
            result.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": int(row["volume"]),
                }
            )
        return result

    async def _fetch_japanese_stock_prices(
        self, symbol: str, start_date: str, end_date: str
    ) -> List[PriceDataPoint]:
        """
        J-Quants APIから日本株の株価データを取得

        Args:
            symbol: 銘柄コード
            start_date: 開始日（YYYY-MM-DD）
            end_date: 終了日（YYYY-MM-DD）

        Returns:
            株価データのリスト
        """
        try:
            prices = await get_jquants_client().get_prices(
                symbol=symbol, start_date=start_date, end_date=end_date
            )

            result = []
            for price in prices:
                result.append(
                    {
                        "date": price["Date"],
                        "open": float(price["AdjO"]),
                        "high": float(price["AdjH"]),
                        "low": float(price["AdjL"]),
                        "close": float(price["AdjC"]),
                        "volume": int(price["AdjVo"]),
                    }
                )
            logger.info(
                "日本株株価を取得しました action=external_io symbol={} start_date={} end_date={} count={}",
                symbol,
                start_date,
                end_date,
                len(result),
            )
            return result
        except Exception as e:
            logger.error(
                "日本株株価の取得に失敗しました action=external_io symbol={} start_date={} end_date={} error={}",
                symbol,
                start_date,
                end_date,
                str(e),
            )
            raise Exception(f"Failed to fetch Japanese stock prices: {str(e)}")

    @staticmethod
    @timed_cache(seconds=3600)  # 1時間キャッシュ
    def _fetch_us_stock_prices_cached(symbol: str, start_date: str, end_date: str) -> List[dict]:
        """
        Stooqから米国株の株価データを取得（キャッシュ付き）

        Args:
            symbol: 銘柄コード
            start_date: 開始日（YYYY-MM-DD）
            end_date: 終了日（YYYY-MM-DD）

        Returns:
            株価データのリスト
        """
        try:
            result = fetch_us_daily_prices_from_stooq(symbol, start_date, end_date)
            logger.info(
                "米国株株価を取得しました action=external_io symbol={} start_date={} end_date={} count={}",
                symbol,
                start_date,
                end_date,
                len(result),
            )
            return result
        except Exception as e:
            logger.error(
                "米国株株価の取得に失敗しました action=external_io symbol={} start_date={} end_date={} error={}",
                symbol,
                start_date,
                end_date,
                str(e),
            )
            raise Exception(f"Failed to fetch US stock prices: {str(e)}")

    async def _fetch_us_stock_prices(
        self, symbol: str, start_date: str, end_date: str
    ) -> List[PriceDataPoint]:
        """
        米国株の株価データを取得（非同期ラッパー）

        Args:
            symbol: 銘柄コード
            start_date: 開始日（YYYY-MM-DD）
            end_date: 終了日（YYYY-MM-DD）

        Returns:
            株価データのリスト
        """
        return self._fetch_us_stock_prices_cached(symbol, start_date, end_date)

    async def get_price_history(
        self,
        symbol: str,
        interval: PriceHistoryInterval = PriceHistoryInterval.DAILY,
        limit: int = 80,
    ) -> dict:
        """
        株価時系列データを取得

        Args:
            symbol: 銘柄コード
            interval: データ間隔
            limit: 取得件数

        Returns:
            株価履歴データ

        Raises:
            ValueError: 投資信託など非対応の証券種別の場合
            Exception: データ取得失敗時
        """
        # 銘柄情報を取得して市場を判定
        from sqlalchemy import select

        result = await self.db.execute(select(Stock).where(Stock.symbol == symbol))
        stock = result.scalar_one_or_none()

        if not stock:
            logger.error("Stockが見つかりませんでした action=select symbol={} found=false", symbol)
            raise ValueError(f"Stock {symbol} not found")

        # 投資信託は非対応
        if stock.security_type == "FUND":
            logger.error("投資信託は価格履歴未対応です action=select symbol={} security_type=FUND", symbol)
            raise ValueError("Price history is not available for investment funds")

        # 開始日・終了日を計算
        start_date = self._calculate_start_date(interval, limit)
        end_date = datetime.now().strftime("%Y-%m-%d")

        # 市場に応じてデータを取得
        if stock.market in ["JPX", "東証", "東証グロース", "東証スタンダード"]:
            data = await self._fetch_japanese_stock_prices(symbol, start_date, end_date)
        else:  # 米国株
            data = await self._fetch_us_stock_prices(symbol, start_date, end_date)

        # 間隔に応じて集計
        if interval == PriceHistoryInterval.WEEKLY:
            data = self._aggregate_to_weekly(data)
        elif interval == PriceHistoryInterval.MONTHLY:
            data = self._aggregate_to_monthly(data)

        # 最新のlimit件のみを返す
        data = data[-limit:] if len(data) > limit else data

        logger.info(
            "PriceHistoryを取得しました action=aggregate symbol={} interval={} limit={} count={}",
            symbol,
            interval.value,
            limit,
            len(data),
        )
        return {"symbol": symbol, "interval": interval.value, "data": data}
