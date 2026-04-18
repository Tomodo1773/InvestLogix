from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stock.schemas import StockWeeklyPerformance
from stock.services.change_reason_service import (
    ChangeReasonSections,
    _format_performers_for_prompt,
    _parse_sections,
    _strip_citations,
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


def _make_marker_text(market: str, top: str, bottom: str) -> str:
    return f"===市場概況===\n{market}\n\n===上昇解説===\n{top}\n\n===下落解説===\n{bottom}\n"


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
        text = "あ" * 300
        assert _trim_to_max_chars(text, max_chars=400) == text

    def test_over_limit_trims_with_ellipsis(self):
        text = "あ" * 600
        result = _trim_to_max_chars(text, max_chars=400)
        assert len(result) <= 400
        assert result.endswith("…")


class TestStripCitations:
    def test_removes_markdown_link_in_parens(self):
        text = "本文 ([diamond.jp](https://diamond.jp/a?x=1)) 続き"
        assert _strip_citations(text) == "本文 続き"

    def test_removes_bare_url(self):
        assert _strip_citations("aaa https://example.com/x bbb") == "aaa bbb"


class TestParseSections:
    def test_parses_three_sections(self):
        text = _make_marker_text("地合いの解説", "上昇の解説", "下落の解説")
        sections = _parse_sections(text)
        assert sections == ChangeReasonSections(
            market_overview="地合いの解説",
            top_commentary="上昇の解説",
            bottom_commentary="下落の解説",
        )

    def test_returns_none_when_marker_missing(self):
        assert _parse_sections("===市場概況===\n本文\n===上昇解説===\n上昇") is None

    def test_returns_none_when_section_empty(self):
        text = _make_marker_text("", "上昇", "下落")
        assert _parse_sections(text) is None


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
    mock_response.output_text = _make_marker_text(
        "今週は地合い改善。",
        "トヨタは好決算で買われた。",
        "任天堂はガイダンス下方修正で売られた。",
    )
    mock_openai_client.responses.create.return_value = mock_response

    top = [_make_perf("7203", "トヨタ自動車", 8.42)]
    bottom = [_make_perf("7974", "任天堂", -6.50)]

    result = await generate_change_reasons(top, bottom)

    assert result == ChangeReasonSections(
        market_overview="今週は地合い改善。",
        top_commentary="トヨタは好決算で買われた。",
        bottom_commentary="任天堂はガイダンス下方修正で売られた。",
    )


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
