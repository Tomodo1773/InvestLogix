"""JQuantsClientの動作確認テスト"""

import os

import pytest
from dotenv import load_dotenv

from stock.services.jquants_service import JQuantsClient


@pytest.fixture
def jquants_client():
    """実際のAPIクライアントを使用するfixture"""
    load_dotenv()
    api_key = os.getenv("JQUANTS_API_KEY")
    if not api_key:
        pytest.skip("環境変数 JQUANTS_API_KEY が設定されていません")
    return JQuantsClient(api_key=api_key)


@pytest.mark.asyncio
async def test_get_prices(jquants_client):
    """株価情報取得の動作確認"""
    # トヨタ自動車の株価を取得
    prices = await jquants_client.get_prices(symbol="7203", start_date="2024-01-01", end_date="2024-01-31")

    assert len(prices) > 0
    price = prices[0]
    assert "O" in price
    assert "H" in price
    assert "L" in price
    assert "C" in price


def test_get_company_info(jquants_client):
    """企業情報取得の動作確認"""
    # トヨタ自動車の企業情報を取得
    company = jquants_client.get_company_info("7203")

    assert company is not None
    assert company["CoName"] == "トヨタ自動車"
    assert company["Code"] == "72030"  # APIは5桁形式で返却
