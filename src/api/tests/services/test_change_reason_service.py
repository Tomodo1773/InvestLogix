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


class TestTrimToMaxChars:
    def test_under_limit_returns_as_is(self):
        text = "あ" * 800
        assert _trim_to_max_chars(text, max_chars=1000) == text

    def test_over_limit_trims_with_ellipsis(self):
        text = "あ" * 1200
        result = _trim_to_max_chars(text, max_chars=1000)
        assert len(result) <= 1000
        assert result.endswith("…")

    def test_trims_at_period_boundary(self):
        body = "第一文です。" + "あ" * 600 + "。" + "い" * 400
        result = _trim_to_max_chars(body, max_chars=1000)
        assert len(result) <= 1000
        assert result.endswith("。…")


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
async def test_generate_change_reasons_success():
    """OpenAI が output_text を返すとき、戻り値が同じ文字列になること"""
    mock_response = MagicMock()
    mock_response.output_text = (
        "上昇トップ: トヨタ自動車は好決算。\n下落ワースト: 任天堂はガイダンス下方修正。"
    )

    mock_client = AsyncMock()
    mock_client.responses.create.return_value = mock_response

    top = [_make_perf("7203", "トヨタ自動車", 8.42)]
    bottom = [_make_perf("7974", "任天堂", -6.50)]

    with patch("stock.services.change_reason_service.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "test-key"
        with patch("stock.services.change_reason_service.get_openai_client", return_value=mock_client):
            result = await generate_change_reasons(top, bottom)

    assert result == mock_response.output_text


@pytest.mark.asyncio
async def test_generate_change_reasons_no_api_key():
    """APIキー未設定時は None を返し、APIを呼ばないこと"""
    mock_client = AsyncMock()

    with patch("stock.services.change_reason_service.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = ""
        with patch("stock.services.change_reason_service.get_openai_client", return_value=mock_client):
            result = await generate_change_reasons(
                [_make_perf("7203", "トヨタ自動車", 8.42)],
                [_make_perf("7974", "任天堂", -6.50)],
            )

    assert result is None
    mock_client.responses.create.assert_not_called()


@pytest.mark.asyncio
async def test_generate_change_reasons_empty_performers():
    """対象銘柄が空の場合は None を返し、APIを呼ばないこと"""
    mock_client = AsyncMock()

    with patch("stock.services.change_reason_service.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "test-key"
        with patch("stock.services.change_reason_service.get_openai_client", return_value=mock_client):
            result = await generate_change_reasons([], [])

    assert result is None
    mock_client.responses.create.assert_not_called()


@pytest.mark.asyncio
async def test_generate_change_reasons_api_error():
    """API 例外時は None を返すこと"""
    mock_client = AsyncMock()
    mock_client.responses.create.side_effect = Exception("API Error")

    with patch("stock.services.change_reason_service.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "test-key"
        with patch("stock.services.change_reason_service.get_openai_client", return_value=mock_client):
            result = await generate_change_reasons(
                [_make_perf("7203", "トヨタ自動車", 8.42)],
                [_make_perf("7974", "任天堂", -6.50)],
            )

    assert result is None


@pytest.mark.asyncio
async def test_generate_change_reasons_empty_output_text():
    """output_text が空文字のときは None を返すこと"""
    mock_response = MagicMock()
    mock_response.output_text = ""

    mock_client = AsyncMock()
    mock_client.responses.create.return_value = mock_response

    with patch("stock.services.change_reason_service.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "test-key"
        with patch("stock.services.change_reason_service.get_openai_client", return_value=mock_client):
            result = await generate_change_reasons(
                [_make_perf("7203", "トヨタ自動車", 8.42)],
                [],
            )

    assert result is None


@pytest.mark.asyncio
async def test_generate_change_reasons_trims_long_output():
    """1000文字超の出力はトリミングされること"""
    mock_response = MagicMock()
    mock_response.output_text = "あ" * 1500

    mock_client = AsyncMock()
    mock_client.responses.create.return_value = mock_response

    with patch("stock.services.change_reason_service.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "test-key"
        with patch("stock.services.change_reason_service.get_openai_client", return_value=mock_client):
            result = await generate_change_reasons(
                [_make_perf("7203", "トヨタ自動車", 8.42)],
                [],
            )

    assert result is not None
    assert len(result) <= 1000
    assert result.endswith("…")


@pytest.mark.asyncio
async def test_generate_change_reasons_uses_expected_openai_params():
    """responses.create が想定パラメータで呼ばれること"""
    mock_response = MagicMock()
    mock_response.output_text = "テスト"

    mock_client = AsyncMock()
    mock_client.responses.create.return_value = mock_response

    with patch("stock.services.change_reason_service.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "test-key"
        with patch("stock.services.change_reason_service.get_openai_client", return_value=mock_client):
            await generate_change_reasons(
                [_make_perf("7203", "トヨタ自動車", 8.42)],
                [_make_perf("7974", "任天堂", -6.50)],
            )

    call_kwargs = mock_client.responses.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-5.4"
    assert call_kwargs["reasoning"] == {"effort": "high"}
    assert call_kwargs["tools"] == [{"type": "web_search"}]
    assert "トヨタ自動車" in call_kwargs["input"]
    assert "任天堂" in call_kwargs["input"]
