"""
J-Quants APIクライアントモジュール
株価情報や銘柄情報の取得を行う

V2 API対応版:
- 認証方式: APIキーのみ（メールアドレス+パスワードは不要）
- ヘッダー: x-api-key
- エンドポイント: /v2/equities/bars/daily
- レスポンス: V2形式をそのまま返す
"""

import asyncio
import os
from typing import Dict, List, Optional

import aiohttp
from dotenv import load_dotenv
from jquantsapi import ClientV2
from loguru import logger

from ..database import settings


class JQuantsClient:
    """J-Quants APIクライアント（V2対応）"""

    BASE_URL = "https://api.jquants.com/v2"

    def __init__(self, api_key: str):
        """
        クライアントの初期化
        Args:
            api_key: J-Quants APIキー
        """
        self.api_key = api_key
        self.client = ClientV2(api_key=api_key)

    async def get_prices(self, symbol: str, start_date: str, end_date: Optional[str] = None) -> List[Dict]:
        """
        指定した銘柄の株価情報を取得する
        Args:
            symbol: 銘柄コード（例: 86970）
            start_date: 開始日（YYYY-MM-DD）
            end_date: 終了日（YYYY-MM-DD）、指定しない場合は当日まで
        Returns:
            株価情報のリスト（V2形式）
        """
        url = f"{self.BASE_URL}/equities/bars/daily"
        headers = {"x-api-key": self.api_key}
        params = {"code": symbol, "from": start_date}
        if end_date:
            params["to"] = end_date

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    error_body = await response.text()
                    logger.error(
                        "J-Quants API error action=external_io status={} params={} error_body={}",
                        response.status,
                        params,
                        error_body,
                    )
                    raise Exception(f"API request failed: {response.status}")
                data = await response.json()
                # V2形式をそのまま返す
                return data.get("data", [])

    def get_company_info(self, symbol: str) -> Optional[Dict]:
        """
        指定した銘柄の企業情報を取得する
        Args:
            symbol: 銘柄コード（例: 86970）
        Returns:
            企業情報の辞書（V2形式）
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


# シングルトンインスタンスの遅延初期化
_jquants_client = None


def get_jquants_client() -> JQuantsClient:
    """JQuantsクライアントのシングルトンインスタンスを取得する"""
    global _jquants_client
    if _jquants_client is None:
        if not settings.JQUANTS_API_KEY:
            raise ValueError("JQUANTS_API_KEY is not configured")
        _jquants_client = JQuantsClient(api_key=settings.JQUANTS_API_KEY)
    return _jquants_client


def test_api():
    """APIの動作テスト"""
    # テスト用の銘柄コード（トヨタ自動車）
    test_symbol = "7203"

    try:
        client = get_jquants_client()

        # 株価情報の取得
        prices = asyncio.run(
            client.get_prices(symbol=test_symbol, start_date="2024-01-01", end_date="2024-02-01")
        )
        logger.info(
            "株価情報を取得しました action=external_io symbol={} count={}",
            test_symbol,
            len(prices),
        )

        # 企業情報の取得
        company = client.get_company_info(test_symbol)
        if company:
            logger.info("企業情報を取得しました action=external_io symbol={}", test_symbol)

        # 市場区分情報の取得
        segments = client.get_market_segment()
        logger.info("市場区分情報を取得しました action=external_io count={}", len(segments))

    except Exception as e:
        logger.error("J-Quants APIのテストに失敗しました action=external_io error={}", str(e))


if __name__ == "__main__":
    # 環境変数の読み込み
    load_dotenv()

    # 認証情報の取得
    api_key = os.getenv("JQUANTS_API_KEY")

    if not api_key:
        logger.error("環境変数 JQUANTS_API_KEY が未設定です action=external_io")
        exit(1)

    # クライアントを初期化
    _jquants_client = JQuantsClient(api_key=api_key)

    # テストの実行
    test_api()
