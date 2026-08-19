import html
import logging
from datetime import datetime
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

# 変動理由の生成に失敗したときにレポートへ差し込む注記
AI_UNAVAILABLE_NOTICE = ":warning: AI解説を取得できませんでした（サマリと騰落ランキングのみ表示しています）"

# 騰落の方向を示す絵文字。Block Kitに文字色の指定は存在しないため、色は絵文字でしか出せない。
# プラス=緑・マイナス=赤はフロントの success / destructive と揃える
EMOJI_UP = "large_green_circle"
EMOJI_DOWN = "red_circle"

# メッセージ全体の地合いを示すヘッダー絵文字。通知一覧でも方向が伝わるようfallbackにも使う
HEADER_EMOJI_UP = ":chart_with_upwards_trend:"
HEADER_EMOJI_DOWN = ":chart_with_downwards_trend:"
HEADER_EMOJI_FLAT = ":bar_chart:"

REPORT_TITLE = "InvestLogix 週次レポート"


async def _get_slack_user_id(user_id: int, db: AsyncSession | None = None) -> str | None:
    """ユーザーに登録されたSlack通知先を取得する。"""
    if db is None:
        return None

    result = await db.execute(select(models.User).where(models.User.user_id == user_id))
    user = result.scalar_one_or_none()
    return user.slack_user_id if user and user.slack_user_id else None


def _escape(text: str) -> str:
    """Slack mrkdwnで特別扱いされる文字をエスケープする。

    tableのセル（raw_text / rich_text）はmrkdwnとして解釈されないため、
    エスケープが必要なのはmrkdwnのtextを持つブロックだけ。
    """
    return html.escape(text, quote=False)


def _format_currency(value: float | None) -> str:
    return f"{int(value or 0):,}円"


def _signed_currency(value: float) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}{_format_currency(abs(value))}"


def _signed_percentage(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def _section_title(text: str) -> dict[str, Any]:
    return {"type": "section", "text": {"type": "mrkdwn", "text": f"*{text}*"}}


def _commentary_block(text: str) -> dict[str, Any]:
    return {"type": "section", "text": {"type": "mrkdwn", "text": _escape(text)}}


def _text_cell(text: str) -> dict[str, Any]:
    return {"type": "raw_text", "text": text}


def _direction_emoji(value: float) -> str:
    return EMOJI_UP if value >= 0 else EMOJI_DOWN


def _header_emoji(weekly_change: float | None) -> str:
    if not weekly_change:
        return HEADER_EMOJI_FLAT
    return HEADER_EMOJI_UP if weekly_change > 0 else HEADER_EMOJI_DOWN


def _period_text(previous_date: datetime | None) -> str:
    """レポートの対象期間。前週の履歴がなければ当日時点として表示する。"""
    today = now_jst()
    if previous_date is None:
        return today.strftime("%Y/%m/%d 時点")
    return f"{previous_date.strftime('%Y/%m/%d')} → {today.strftime('%m/%d')}"


def _weekly_change_block(weekly_change: float) -> dict[str, Any]:
    """週次レポートの主役である前週比を、サマリ表から独立した1行として強調する。"""
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f":{_direction_emoji(weekly_change)}: *前週比*  {_signed_currency(weekly_change)}",
        },
    }


def _summary_table(portfolio_data: dict[str, Any]) -> dict[str, Any]:
    """資産サマリを「左=項目名・右=値」の表にする。

    section.fieldsは「ラベルの下に値」を2カラムに並べる形式で、値の長さが不揃いだと
    セルの高さが揃わず行がガタつくため、項目名と値が必ず対になるtableを使う。
    """
    total_pl = float(portfolio_data["total_pl"])
    total_pl_percentage = float(portfolio_data["total_pl_percentage"])
    rows = [
        ("時価総額", _format_currency(portfolio_data["total_market_value"])),
        ("取得価格", _format_currency(portfolio_data["total_cost"])),
        ("総損益", f"{_signed_currency(total_pl)} ({_signed_percentage(total_pl_percentage)})"),
        # 実現損益は損切りでマイナスになりうるので、総損益と同じく符号を付ける。
        # 残高（時価総額・取得価格）と常に正の配当総額は符号なし
        ("実現損益", _signed_currency(float(portfolio_data["total_realized_pl"]))),
        ("配当総額", _format_currency(portfolio_data["total_dividend"])),
    ]
    return {
        "type": "table",
        "column_settings": [{"align": "left"}, {"align": "right"}],
        "rows": [[_text_cell(label), _text_cell(value)] for label, value in rows],
    }


def _performer_row(rank: int, performer: StockWeeklyPerformance) -> list[dict[str, Any]]:
    rate_cell = {
        "type": "rich_text",
        "elements": [
            {
                "type": "rich_text_section",
                "elements": [
                    {"type": "emoji", "name": _direction_emoji(performer.change_rate)},
                    {"type": "text", "text": f" {_signed_percentage(performer.change_rate)}"},
                ],
            }
        ],
    }
    return [_text_cell(f"{rank}. {performer.name} ({performer.symbol})"), rate_cell]


def _ranking_block(performers: list[StockWeeklyPerformance]) -> dict[str, Any]:
    if not performers:
        return {"type": "section", "text": {"type": "mrkdwn", "text": "データなし"}}

    rows = [[_text_cell("銘柄"), _text_cell("騰落率")]]
    rows.extend(_performer_row(rank, performer) for rank, performer in enumerate(performers[:5], 1))
    return {
        "type": "table",
        "column_settings": [{"align": "left", "is_wrapped": True}, {"align": "right"}],
        "rows": rows,
    }


def _fallback_text(weekly_change: float | None) -> str:
    """モバイルのプッシュ通知に出る文言。開かずに結論が分かるよう前週比まで載せる。"""
    title = f"{_header_emoji(weekly_change)} {REPORT_TITLE}"
    if weekly_change is None:
        return title
    return f"{title} ｜ 前週比 {_signed_currency(weekly_change)}"


def _build_weekly_report_blocks(
    portfolio_data: dict[str, Any],
    top_performers: list[StockWeeklyPerformance],
    bottom_performers: list[StockWeeklyPerformance],
    sections: ChangeReasonSections | None,
) -> list[dict[str, Any]]:
    """週次レポートをSlack Block Kitのメッセージに変換する。"""
    weekly_change = portfolio_data.get("weekly_change")
    weekly_change = float(weekly_change) if weekly_change is not None else None

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{_header_emoji(weekly_change)} {REPORT_TITLE}"},
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": _period_text(portfolio_data.get("previous_date"))}],
        },
    ]
    if weekly_change is not None:
        blocks.append(_weekly_change_block(weekly_change))
    blocks.append(_summary_table(portfolio_data))
    blocks.append({"type": "divider"})

    if sections:
        blocks.extend([_section_title("マーケット概況"), _commentary_block(sections.market_overview)])
    else:
        # 生成に失敗した旨を明示する。これがないと解説が消えた原因が
        # 外部APIの失敗なのか実装の欠落なのかレポートから判別できない
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": AI_UNAVAILABLE_NOTICE}]})

    blocks.extend([_section_title("上昇トップ5"), _ranking_block(top_performers)])
    if sections:
        blocks.append(_commentary_block(sections.top_commentary))

    blocks.extend([_section_title("下落ワースト5"), _ranking_block(bottom_performers)])
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

    weekly_change = portfolio_data.get("weekly_change")

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

            post_result = await _call_slack_api(
                client,
                SLACK_POST_MESSAGE_URL,
                token,
                {
                    "channel": channel_id,
                    "text": _fallback_text(float(weekly_change) if weekly_change is not None else None),
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
