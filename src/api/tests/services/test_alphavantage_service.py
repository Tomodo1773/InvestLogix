from datetime import date

import pytest

from stock.services import alphavantage_service


class MockResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def json(self) -> dict:
        return self.payload


class MockAsyncClient:
    responses: list[dict] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str) -> MockResponse:
        return MockResponse(self.responses.pop(0))


@pytest.mark.asyncio
async def test_fetch_usdjpy_daily_rates_does_not_cache_failed_response(monkeypatch):
    """日次為替取得の失敗結果はキャッシュしない"""
    alphavantage_service.fetch_usdjpy_daily_rates.cache.clear()
    MockAsyncClient.responses = [
        {},
        {"Time Series FX (Daily)": {"2024-01-30": {"4. close": "150.25"}}},
    ]
    monkeypatch.setattr(alphavantage_service.httpx, "AsyncClient", MockAsyncClient)

    with pytest.raises(KeyError):
        await alphavantage_service.fetch_usdjpy_daily_rates()

    rates = await alphavantage_service.fetch_usdjpy_daily_rates()

    assert rates == {date(2024, 1, 30): 150.25}
