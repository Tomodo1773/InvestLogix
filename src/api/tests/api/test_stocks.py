import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from stock.schemas import StockCreate, UserCreate
from stock.services.auth_service import AuthService
from tests.conftest import client, db_session


@pytest.mark.asyncio
async def test_create_japanese_stock(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """
    日本株銘柄登録のテスト
    - 期待する動作:
        - ステータスコード200
        - 登録された日本株情報を返却
    """
    stock_data = StockCreate(symbol="8058")  # 三菱商事のシンボル
    response = await client.post(
        "/api/v1/stocks/", json=stock_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "8058"
    assert data["market"] == "JPX"
    assert data["security_type"] == "STOCK"


@pytest.mark.asyncio
async def test_create_us_stock(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """
    米国株銘柄登録のテスト
    - 期待する動作:
        - ステータスコード200
        - 登録された米国株情報を返却
    """
    stock_data = StockCreate(symbol="AAPL")  # Appleのシンボル
    response = await client.post(
        "/api/v1/stocks/", json=stock_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["market"] == "NASDAQ"
    assert data["security_type"] == "STOCK"


@pytest.mark.asyncio
async def test_create_us_etf(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """
    米国ETF銘柄登録のテスト
    - 期待する動作:
        - ステータスコード200
        - 登録されたETF情報を返却
    """
    stock_data = StockCreate(symbol="SPYD")  # SPYDのシンボル
    response = await client.post(
        "/api/v1/stocks/", json=stock_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "SPYD"
    assert data["market"] == "United States"
    assert data["security_type"] == "ETF"


@pytest.mark.asyncio
async def test_create_investment_trust(client: AsyncClient, db_session: AsyncSession, auth_token: str):
    """
    投資信託登録のテスト
    - 期待する動作:
        - ステータスコード200
        - 登録された投資信託情報を返却
    """
    stock_data = StockCreate(symbol="JP90C000J569")  # 投資信託のシンボル
    response = await client.post(
        "/api/v1/stocks/", json=stock_data.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "JP90C000J569"
    assert data["market"] == "JPX"
    assert data["security_type"] == "FUND"
