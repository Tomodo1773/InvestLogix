"""週次レポートのBlock Kit組み立てのテスト。"""

from datetime import datetime
from typing import Any

import pytest

from stock.schemas import StockWeeklyPerformance
from stock.services.change_reason_service import ChangeReasonSections
from stock.services.notification_service import (
    AI_UNAVAILABLE_NOTICE,
    EMOJI_DOWN,
    EMOJI_UP,
    HEADER_EMOJI_DOWN,
    HEADER_EMOJI_UP,
    _build_weekly_report_blocks,
    _fallback_text,
)


def _make_perf(symbol: str, name: str, change_rate: float) -> StockWeeklyPerformance:
    return StockWeeklyPerformance(
        symbol=symbol,
        name=name,
        latest_price=100.0,
        old_price=100.0,
        change_rate=change_rate,
    )


def _portfolio_data(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "total_cost": 5_000_000,
        "total_market_value": 5_432_100,
        "total_pl": 432_100,
        "total_pl_percentage": 8.64,
        "total_realized_pl": 12_000,
        "total_dividend": 34_500,
        "weekly_change": 123_456,
        "previous_date": datetime(2026, 8, 12),
    }
    data.update(overrides)
    return data


@pytest.fixture(autouse=True)
def fixed_today(mocker):
    """対象期間の表示は当日を基準にするため、テスト中は日付を固定する。"""
    mocker.patch(
        "stock.services.notification_service.now_jst",
        return_value=datetime(2026, 8, 19),
    )


@pytest.fixture
def sections() -> ChangeReasonSections:
    return ChangeReasonSections(
        market_overview="今週の地合いはこう。",
        top_commentary="上げた理由はこう。",
        bottom_commentary="下げた理由はこう。",
    )


@pytest.fixture
def top_performers() -> list[StockWeeklyPerformance]:
    return [_make_perf("7203", "トヨタ自動車", 5.2), _make_perf("6758", "ソニーグループ", 3.81)]


@pytest.fixture
def bottom_performers() -> list[StockWeeklyPerformance]:
    return [_make_perf("9984", "ソフトバンクグループ", -4.12)]


def _blocks_of_type(blocks: list[dict[str, Any]], block_type: str) -> list[dict[str, Any]]:
    return [block for block in blocks if block["type"] == block_type]


def _tables(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _blocks_of_type(blocks, "table")


def test_summary_is_a_table_of_label_value_pairs(top_performers, bottom_performers, sections):
    blocks = _build_weekly_report_blocks(_portfolio_data(), top_performers, bottom_performers, sections)

    summary = _tables(blocks)[0]

    assert summary["column_settings"] == [{"align": "left"}, {"align": "right"}]
    assert [[cell["text"] for cell in row] for row in summary["rows"]] == [
        ["時価総額", "5,432,100円"],
        ["取得価格", "5,000,000円"],
        ["総損益", "+432,100円 (+8.64%)"],
        ["実現損益", "+12,000円"],
        ["配当総額", "34,500円"],
    ]


def test_ranking_numbers_the_names_and_colors_the_rate(top_performers, bottom_performers, sections):
    blocks = _build_weekly_report_blocks(_portfolio_data(), top_performers, bottom_performers, sections)

    top_table, bottom_table = _tables(blocks)[1:3]

    assert [cell["text"] for cell in top_table["rows"][0]] == ["銘柄", "騰落率"]

    name_cell, rate_cell = top_table["rows"][1]
    assert name_cell["text"] == "1. トヨタ自動車 (7203)"
    assert rate_cell["elements"][0]["elements"] == [
        {"type": "emoji", "name": EMOJI_UP},
        {"type": "text", "text": " +5.20%"},
    ]
    assert top_table["rows"][2][0]["text"] == "2. ソニーグループ (6758)"

    loss_name_cell, loss_rate_cell = bottom_table["rows"][1]
    assert loss_name_cell["text"] == "1. ソフトバンクグループ (9984)"
    assert loss_rate_cell["elements"][0]["elements"] == [
        {"type": "emoji", "name": EMOJI_DOWN},
        {"type": "text", "text": " -4.12%"},
    ]


@pytest.mark.parametrize(
    ("weekly_change", "expected_emoji", "expected_amount"),
    [(123_456, HEADER_EMOJI_UP, "+123,456円"), (-98_765, HEADER_EMOJI_DOWN, "-98,765円")],
)
def test_header_and_weekly_change_follow_the_direction(
    top_performers, bottom_performers, sections, weekly_change, expected_emoji, expected_amount
):
    blocks = _build_weekly_report_blocks(
        _portfolio_data(weekly_change=weekly_change), top_performers, bottom_performers, sections
    )

    assert blocks[0]["text"]["text"] == f"{expected_emoji} InvestLogix 週次レポート"
    assert blocks[1]["elements"][0]["text"] == "2026/08/12 → 08/19"
    assert expected_amount in blocks[2]["text"]["text"]


def test_weekly_change_block_is_omitted_without_previous_history(top_performers, bottom_performers, sections):
    blocks = _build_weekly_report_blocks(
        _portfolio_data(weekly_change=None, previous_date=None),
        top_performers,
        bottom_performers,
        sections,
    )

    assert "前週比" not in blocks[2].get("text", {}).get("text", "")
    assert blocks[1]["elements"][0]["text"].endswith("時点")


def test_ai_failure_is_reported_in_place_of_the_commentary(top_performers, bottom_performers):
    blocks = _build_weekly_report_blocks(_portfolio_data(), top_performers, bottom_performers, None)

    notices = [
        element["text"]
        for block in _blocks_of_type(blocks, "context")
        for element in block["elements"]
        if element["text"] == AI_UNAVAILABLE_NOTICE
    ]
    assert notices == [AI_UNAVAILABLE_NOTICE]


def test_ranking_falls_back_to_a_message_when_empty(bottom_performers, sections):
    blocks = _build_weekly_report_blocks(_portfolio_data(), [], bottom_performers, sections)

    assert {"type": "section", "text": {"type": "mrkdwn", "text": "データなし"}} in blocks


def test_fallback_text_carries_the_weekly_change():
    assert _fallback_text(123_456) == f"{HEADER_EMOJI_UP} InvestLogix 週次レポート ｜ 前週比 +123,456円"
    assert _fallback_text(None) == ":bar_chart: InvestLogix 週次レポート"
