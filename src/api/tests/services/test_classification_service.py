from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stock.services.classification_service import classify_fund_currency


@pytest.mark.asyncio
async def test_classify_fund_currency_usd():
    """米国株ファンドがUSDに分類されること"""
    mock_parsed = MagicMock()
    mock_parsed.currency = "USD"

    mock_response = MagicMock()
    mock_response.output_parsed = mock_parsed

    with patch("stock.services.classification_service.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "test-key"
        with patch("stock.services.classification_service.AsyncOpenAI") as mock_openai_cls:
            mock_client = AsyncMock()
            mock_client.responses.parse.return_value = mock_response
            mock_openai_cls.return_value = mock_client

            result = await classify_fund_currency("eMAXIS Slim 米国株式(S&P500)")
            assert result == "USD"


@pytest.mark.asyncio
async def test_classify_fund_currency_fallback_on_error():
    """API呼び出し失敗時にJPYにフォールバックすること"""
    with patch("stock.services.classification_service.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "test-key"
        with patch("stock.services.classification_service.AsyncOpenAI") as mock_openai_cls:
            mock_client = AsyncMock()
            mock_client.responses.parse.side_effect = Exception("API Error")
            mock_openai_cls.return_value = mock_client

            result = await classify_fund_currency("テストファンド")
            assert result == "JPY"


@pytest.mark.asyncio
async def test_classify_fund_currency_no_api_key():
    """APIキー未設定時にJPYを返すこと"""
    with patch("stock.services.classification_service.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = ""

        result = await classify_fund_currency("eMAXIS Slim 米国株式(S&P500)")
        assert result == "JPY"
