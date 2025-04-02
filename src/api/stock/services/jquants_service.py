"""
J-Quants APIクライアントモジュール
株価情報や銘柄情報の取得を行う
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import aiohttp
from dotenv import load_dotenv
from jquantsapi.client import Client

from ..database import settings


class JQuantsClient:
    """J-Quants APIクライアント"""

    BASE_URL = "https://api.jquants.com/v1"

    def __init__(self, mail_address: str, password: str):
        """
        クライアントの初期化
        Args:
            mail_address: J-Quants APIログイン用メールアドレス
            password: J-Quants APIログイン用パスワード
        """
        self.client = Client(mail_address=mail_address, password=password)
        self._refresh_token = None
        self._id_token = None
        self._token_expires_at = None

    def authenticate(self) -> None:
        """
        認証を行い、トークンを取得する
        トークンの有効期限が切れている場合は再取得する
        """
        if not self._is_token_valid():
            self._refresh_token = self.client.get_refresh_token()
            self._id_token = self.client.get_id_token(self._refresh_token)
            self._token_expires_at = datetime.now() + timedelta(hours=23)  # トークンの有効期限は24時間

    def _is_token_valid(self) -> bool:
        """トークンが有効かどうかを確認する"""
        if not self._token_expires_at:
            return False
        # 有効期限の1時間前に更新する
        return datetime.now() < (self._token_expires_at - timedelta(hours=1))

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
        self.authenticate()
        url = f"{self.BASE_URL}/prices/daily_quotes"
        headers = {"Authorization": f"Bearer {self._id_token}"}
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
        self.authenticate()
        response = self.client.get_listed_info(code=symbol)
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
        self.authenticate()
        response = self.client.get_market_segments()
        return response.to_dict("records") if not response.empty else []


# シングルトンインスタンスの作成（環境変数から認証情報を取得）
jquants_client = JQuantsClient(mail_address=settings.JQUANTS_MAIL_ADDRESS, password=settings.JQUANTS_PASSWORD)


def test_api():
    """APIの動作テスト"""
    # テスト用の銘柄コード（トヨタ自動車）
    test_symbol = "7203"

    try:
        # 株価情報の取得
        prices = asyncio.run(jquants_client.get_prices(symbol=test_symbol, start_date="2024-01-01", end_date="2024-02-01"))
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
    mail_address = os.getenv("JQUANTS_MAIL_ADDRESS")
    password = os.getenv("JQUANTS_PASSWORD")

    if not mail_address or not password:
        print("環境変数 JQUANTS_MAIL_ADDRESS と JQUANTS_PASSWORD を設定してください。")
        exit(1)

    # クライアントの初期化（シングルトンインスタンスを上書き）
    jquants_client = JQuantsClient(mail_address=mail_address, password=password)

    # テストの実行
    test_api()
