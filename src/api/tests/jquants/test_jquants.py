"""JQuantsClientの動作確認テスト"""

import os

import pytest
from dotenv import load_dotenv

from api.stock.services.jquants_service import JQuantsClient


@pytest.fixture
def jquants_client():
    """実際のAPIクライアントを使用するfixture"""
    load_dotenv()
    mail_address = os.getenv("JQUANTS_MAIL_ADDRESS")
    password = os.getenv("JQUANTS_PASSWORD")
    if not mail_address or not password:
        pytest.skip("環境変数 JQUANTS_MAIL_ADDRESS と JQUANTS_PASSWORD が設定されていません")
    return JQuantsClient(mail_address=mail_address, password=password)


@pytest.mark.asyncio
async def test_get_prices(jquants_client):
    """株価情報取得の動作確認"""
    # トヨタ自動車の株価を取得
    prices = await jquants_client.get_prices(symbol="7203", start_date="2024-01-01", end_date="2024-01-31")

    assert len(prices) > 0
    price = prices[0]
    assert "Open" in price
    assert "High" in price
    assert "Low" in price
    assert "Close" in price


def test_get_company_info(jquants_client):
    """企業情報取得の動作確認"""
    # トヨタ自動車の企業情報を取得
    company = jquants_client.get_company_info("7203")

    assert company is not None
    assert company["CompanyName"] == "トヨタ自動車"
    assert company["Code"] == "72030"  # APIは5桁形式で返却
