from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stock.schemas import StockWeeklyPerformance
from stock.services.change_reason_service import (
    _format_performers_for_prompt,
    _trim_to_max_chars,
    generate_change_reasons,
)


def _make_perf(symbol: str, name: str, change_rate: float) -> StockWeeklyPerformance:
    return StockWeeklyPerformance(
        symbol=symbol,
        name=name,
        latest_price=100.0,
        old_price=100.0,
        change_rate=change_rate,
    )


@pytest.fixture
def mock_settings():
    with patch("stock.services.change_reason_service.settings") as m:
        m.OPENAI_API_KEY = "test-key"
        yield m


@pytest.fixture
def mock_openai_client():
    client = AsyncMock()
    with patch("stock.services.change_reason_service.get_openai_client", return_value=client):
        yield client


class TestTrimToMaxChars:
    def test_under_limit_returns_as_is(self):
        text = "あ" * 800
        assert _trim_to_max_chars(text, max_chars=1000) == text

    def test_over_limit_trims_with_ellipsis(self):
        text = "あ" * 1200
        result = _trim_to_max_chars(text, max_chars=1000)
        assert len(result) <= 1000
        assert result.endswith("…")


class TestFormatPerformersForPrompt:
    def test_includes_name_symbol_and_change_rate(self):
        top = [_make_perf("7203", "トヨタ自動車", 8.42)]
        bottom = [_make_perf("NVDA", "NVIDIA", -5.12)]

        result = _format_performers_for_prompt(top, bottom)

        assert "トヨタ自動車" in result
        assert "7203" in result
        assert "+8.42%" in result
        assert "NVIDIA" in result
        assert "NVDA" in result
        assert "-5.12%" in result
        assert "【上昇トップ】" in result
        assert "【下落ワースト】" in result


@pytest.mark.asyncio
async def test_generate_change_reasons_success(mock_settings, mock_openai_client):
    mock_response = MagicMock()
    mock_response.output_text = (
        "上昇トップ: トヨタ自動車は好決算。\n下落ワースト: 任天堂はガイダンス下方修正。"
    )
    mock_openai_client.responses.create.return_value = mock_response

    top = [_make_perf("7203", "トヨタ自動車", 8.42)]
    bottom = [_make_perf("7974", "任天堂", -6.50)]

    result = await generate_change_reasons(top, bottom)

    assert result == mock_response.output_text


@pytest.mark.asyncio
async def test_generate_change_reasons_no_api_key(mock_settings, mock_openai_client):
    mock_settings.OPENAI_API_KEY = ""

    result = await generate_change_reasons(
        [_make_perf("7203", "トヨタ自動車", 8.42)],
        [_make_perf("7974", "任天堂", -6.50)],
    )

    assert result is None
    mock_openai_client.responses.create.assert_not_called()


@pytest.mark.asyncio
async def test_generate_change_reasons_api_error(mock_settings, mock_openai_client):
    mock_openai_client.responses.create.side_effect = Exception("API Error")

    result = await generate_change_reasons(
        [_make_perf("7203", "トヨタ自動車", 8.42)],
        [_make_perf("7974", "任天堂", -6.50)],
    )

    assert result is None


@pytest.mark.asyncio
async def test_generate_change_reasons_trims_long_output(mock_settings, mock_openai_client):
    mock_response = MagicMock()
    mock_response.output_text = "あ" * 1500
    mock_openai_client.responses.create.return_value = mock_response

    result = await generate_change_reasons(
        [_make_perf("7203", "トヨタ自動車", 8.42)],
        [],
    )

    assert result is not None
    assert len(result) <= 1000
    assert result.endswith("…")
