"""
J-Quants APIクライアントモジュール
株価情報や銘柄情報の取得を行う
"""

import asyncio
import os
from typing import Dict, List, Optional

import aiohttp
from dotenv import load_dotenv
from jquantsapi import ClientV2

from ..database import settings


class JQuantsClient:
    """J-Quants APIクライアント（v2対応）"""

    BASE_URL = "https://api.jquants.com/v2"

    def __init__(self, api_key: str = ""):
        """
        クライアントの初期化
        Args:
            api_key: J-Quants APIキー。指定しない場合は環境変数JQUANTS_API_KEYから取得
        """
        self.client = ClientV2(api_key=api_key) if api_key else ClientV2()

    async def get_prices(self, symbol: str, start_date: str, end_date: str = None) -> List[Dict]:
        """
        指定した銘柄の株価情報を取得する
        Args:
            symbol: 銘柄コード（例: 86970）
            start_date: 開始日（YYYY-MM-DD）
            end_date: 終了日（YYYY-MM-DD）、指定しない場合は当日まで
        Returns:
            株価情報のリスト
        """
        url = f"{self.BASE_URL}/prices/daily_quotes"
        headers = {"x-api-key": self.client._api_key}
        params = {"code": symbol, "from": start_date}
        if end_date:
            params["to"] = end_date

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    raise Exception(f"API request failed: {response.status}")
                data = await response.json()
                return data.get("daily_quotes", [])

    def get_company_info(self, symbol: str) -> Optional[Dict]:
        """
        指定した銘柄の企業情報を取得する
        Args:
            symbol: 銘柄コード（例: 86970）
        Returns:
            企業情報の辞書
        """
        response = self.client.get_eq_master(code=symbol)
        if response.empty:
            return None
        return response.iloc[0].to_dict()

    def get_market_segment(self, symbol: str = "") -> List[Dict]:
        """
        市場区分情報を取得する
        Args:
            symbol: 銘柄コード（省略可）
        Returns:
            市場区分情報のリスト
        """
        response = self.client.get_market_segments()
        return response.to_dict("records") if not response.empty else []


# シングルトンインスタンスの作成（環境変数から認証情報を取得）
jquants_client = JQuantsClient(api_key=settings.JQUANTS_API_KEY)


def test_api():
    """APIの動作テスト"""
    # テスト用の銘柄コード（トヨタ自動車）
    test_symbol = "7203"

    try:
        # 株価情報の取得
        prices = asyncio.run(
            jquants_client.get_prices(symbol=test_symbol, start_date="2024-01-01", end_date="2024-02-01")
        )
        print("\n=== 株価情報 ===")
        print(f"取得件数: {len(prices)}")
        if prices:
            print("最新の株価:", prices[0])

        # 企業情報の取得
        company = jquants_client.get_company_info(test_symbol)
        print("\n=== 企業情報 ===")
        if company:
            print("企業情報", company)

        # 市場区分情報の取得
        segments = jquants_client.get_market_segment()
        print("\n=== 市場区分情報 ===")
        print(f"取得件数: {len(segments)}")
        if segments:
            print("市場区分:", segments)

    except Exception as e:
        print(f"エラーが発生しました: {e}")


if __name__ == "__main__":
    # 環境変数の読み込み
    load_dotenv()

    # 認証情報の取得
    api_key = os.getenv("JQUANTS_API_KEY")

    if not api_key:
        print("環境変数 JQUANTS_API_KEY を設定してください。")
        exit(1)

    # クライアントの初期化（シングルトンインスタンスを上書き）
    jquants_client = JQuantsClient(api_key=api_key)

    # テストの実行
    test_api()
