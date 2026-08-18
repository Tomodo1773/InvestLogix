import html
import logging
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from ..database import settings
from ..schemas import StockWeeklyPerformance
from ..utils.datetime import now_jst
from .change_reason_service import ChangeReasonSections

logger = logging.getLogger(__name__)

SLACK_OPEN_DM_URL = "https://slack.com/api/conversations.open"
SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"
SLACK_REQUEST_TIMEOUT_SECONDS = 30.0


async def _get_slack_user_id(user_id: int, db: AsyncSession | None = None) -> str | None:
    """ユーザーに登録されたSlack通知先を取得する。"""
    if db is None:
        return None

    result = await db.execute(select(models.User).where(models.User.user_id == user_id))
    user = result.scalar_one_or_none()
    return user.slack_user_id if user and user.slack_user_id else None


def _escape(text: str) -> str:
    """Slack mrkdwnで特別扱いされる文字をエスケープする。"""
    return html.escape(text, quote=False)


def _format_currency(value: float | None) -> str:
    return f"{int(value or 0):,}円"


def _format_percentage(value: float | None) -> str:
    return f"{value or 0:.2f}%"


def _direction(value: float) -> str:
    if value > 0:
        return "▲"
    if value < 0:
        return "▼"
    return "―"


def _signed_currency(value: float) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{_direction(value)} {sign}{_format_currency(abs(value))}"


def _signed_percentage(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{_direction(value)} {sign}{value:.2f}%"


def _field(label: str, value: str) -> dict[str, Any]:
    return {"type": "mrkdwn", "text": f"*{label}*\n{value}"}


def _section_title(text: str) -> dict[str, Any]:
    return {"type": "section", "text": {"type": "mrkdwn", "text": f"*{text}*"}}


def _build_summary_fields(portfolio_data: dict[str, Any]) -> list[dict[str, Any]]:
    total_pl = float(portfolio_data["total_pl"])
    total_pl_percentage = float(portfolio_data["total_pl_percentage"])
    fields = [
        _field("取得価格", _format_currency(portfolio_data["total_cost"])),
        _field("時価総額", _format_currency(portfolio_data["total_market_value"])),
    ]

    weekly_change = portfolio_data.get("weekly_change")
    if weekly_change is not None:
        fields.append(_field("前週比", _signed_currency(float(weekly_change))))

    fields.extend(
        [
            _field(
                "総損益",
                f"{_signed_currency(total_pl)} ({_signed_percentage(total_pl_percentage)})",
            ),
            _field("実現損益", _format_currency(portfolio_data["total_realized_pl"])),
            _field("配当総額", _format_currency(portfolio_data["total_dividend"])),
        ]
    )
    return fields


def _build_ranking_block(performers: list[StockWeeklyPerformance]) -> dict[str, Any]:
    if not performers:
        return {"type": "section", "text": {"type": "mrkdwn", "text": "データなし"}}

    fields: list[dict[str, Any]] = []
    for rank, performer in enumerate(performers[:5], 1):
        fields.extend(
            [
                _field(f"{rank}. {_escape(performer.name)}", f"`{_escape(performer.symbol)}`"),
                _field("騰落率", _signed_percentage(performer.change_rate)),
            ]
        )
    return {"type": "section", "fields": fields}


def _commentary_block(text: str) -> dict[str, Any]:
    return {"type": "section", "text": {"type": "mrkdwn", "text": _escape(text)}}


def _build_weekly_report_blocks(
    portfolio_data: dict[str, Any],
    top_performers: list[StockWeeklyPerformance],
    bottom_performers: list[StockWeeklyPerformance],
    sections: ChangeReasonSections | None,
) -> list[dict[str, Any]]:
    """週次レポートをSlack Block Kitのメッセージに変換する。"""
    blocks: list[dict[str, Any]] = [
        {"type": "header", "text": {"type": "plain_text", "text": "InvestLogix 週次レポート"}},
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": now_jst().strftime("%Y/%m/%d 時点")},
            ],
        },
        {"type": "divider"},
        _section_title("資産サマリ"),
        {"type": "section", "fields": _build_summary_fields(portfolio_data)},
    ]

    if sections:
        blocks.extend(
            [
                {"type": "divider"},
                _section_title("マーケット概況"),
                _commentary_block(sections.market_overview),
            ]
        )

    blocks.extend(
        [
            {"type": "divider"},
            _section_title("上昇トップ5"),
            _build_ranking_block(top_performers),
        ]
    )
    if sections:
        blocks.append(_commentary_block(sections.top_commentary))

    blocks.extend(
        [
            {"type": "divider"},
            _section_title("下落ワースト5"),
            _build_ranking_block(bottom_performers),
        ]
    )
    if sections:
        blocks.append(_commentary_block(sections.bottom_commentary))

    return blocks


async def _call_slack_api(
    client: httpx.AsyncClient,
    url: str,
    token: str,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    response = await client.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
    )
    if response.status_code != 200:
        logger.error("Slack APIがHTTPエラーを返しました status_code=%s", response.status_code)
        return None

    try:
        body = response.json()
    except ValueError:
        logger.error("Slack APIレスポンスをJSONとして解析できませんでした")
        return None

    if not body.get("ok"):
        logger.error("Slack APIがエラーを返しました error=%s", body.get("error", "unknown"))
        return None
    return body


async def send_weekly_summary_notification(
    user_id: int,
    portfolio_data: dict[str, Any],
    top_performers: list[StockWeeklyPerformance],
    bottom_performers: list[StockWeeklyPerformance],
    sections: ChangeReasonSections | None,
    db: AsyncSession | None = None,
) -> bool:
    """週次レポートをSlackアプリとのDMへ送信する。"""
    token = settings.SLACK_BOT_TOKEN
    if not token:
        logger.error("SLACK_BOT_TOKENが設定されていません")
        return False

    slack_user_id = await _get_slack_user_id(user_id, db)
    if not slack_user_id:
        logger.error("Slack User IDが設定されていません user_id=%s", user_id)
        return False

    try:
        async with httpx.AsyncClient(timeout=SLACK_REQUEST_TIMEOUT_SECONDS) as client:
            open_result = await _call_slack_api(
                client,
                SLACK_OPEN_DM_URL,
                token,
                {"users": slack_user_id},
            )
            channel_id = open_result.get("channel", {}).get("id") if open_result else None
            if not channel_id:
                logger.error("Slack DMのChannel IDを取得できませんでした user_id=%s", user_id)
                return False

            today = now_jst().strftime("%Y/%m/%d")
            post_result = await _call_slack_api(
                client,
                SLACK_POST_MESSAGE_URL,
                token,
                {
                    "channel": channel_id,
                    "text": f"InvestLogix 週次レポート（{today}）",
                    "blocks": _build_weekly_report_blocks(
                        portfolio_data,
                        top_performers,
                        bottom_performers,
                        sections,
                    ),
                },
            )
    except httpx.HTTPError:
        logger.exception("Slack通知の通信に失敗しました user_id=%s", user_id)
        return False

    if post_result:
        logger.info("週次レポートをSlackへ送信しました user_id=%s", user_id)
        return True
    return False
