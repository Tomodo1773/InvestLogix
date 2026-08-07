import logging
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from ..database import settings
from ..utils.datetime import now_jst
from .change_reason_service import ChangeReasonSections

logger = logging.getLogger(__name__)

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"

# Flex Message 用カラー定数。損益・騰落率の方向色はバブル内で統一する。
COLOR_PROFIT = "#1DB446"
COLOR_LOSS = "#DB2C2C"
COLOR_TEXT_PRIMARY = "#111111"
COLOR_TEXT_SECONDARY = "#555555"
COLOR_TEXT_MUTED = "#999999"
COLOR_HEADING = "#333333"
COLOR_SEPARATOR = "#E0E0E0"
COLOR_BACKGROUND = "#FFFFFF"


class NotificationService:
    """LINE通知サービス（ユーザーIDの解決などの共通処理を提供）"""

    @staticmethod
    async def get_line_user_id(user_id: int, db: AsyncSession = None) -> str | None:
        """指定されたユーザーIDに対応するLINE UserIDを取得する"""
        if db is None:
            return None

        query = select(models.User).where(models.User.user_id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user or not user.line_user_id:
            return None

        return user.line_user_id


def _format_currency(value: float) -> str:
    if value is None:
        return "0"
    return f"{int(value):,}"


def _format_decimal(value: float) -> str:
    if value is None:
        return "0.00"
    return f"{value:.2f}"


def _get_profit_loss_color(percentage: float) -> str:
    if percentage > 0:
        return COLOR_PROFIT
    if percentage < 0:
        return COLOR_LOSS
    return COLOR_TEXT_PRIMARY


def _build_ranking_row(rank: int, name: str, symbol: str, change_rate: float) -> dict:
    """ランキングの1行分のFlex Boxを作成する"""
    sign = "+" if change_rate >= 0 else ""

    return {
        "type": "box",
        "layout": "horizontal",
        "contents": [
            {"type": "text", "text": f"{rank}.", "size": "sm", "flex": 0, "color": COLOR_TEXT_SECONDARY},
            {
                "type": "text",
                "text": f"{name}({symbol})",
                "size": "sm",
                "flex": 3,
                "margin": "sm",
                "color": COLOR_HEADING,
            },
            {
                "type": "text",
                "text": f"{sign}{change_rate:.2f}%",
                "size": "sm",
                "align": "end",
                "color": _get_profit_loss_color(change_rate),
                "weight": "bold",
                "flex": 1,
            },
        ],
        "margin": "md",
    }


def _section_heading(text: str) -> dict:
    return {
        "type": "text",
        "text": text,
        "weight": "bold",
        "size": "md",
        "margin": "lg",
        "color": COLOR_HEADING,
    }


def _section_body(text: str, margin: str = "md") -> dict:
    return {
        "type": "text",
        "text": text,
        "wrap": True,
        "size": "sm",
        "margin": margin,
        "color": COLOR_TEXT_SECONDARY,
    }


def _ranking_contents(performers: list) -> list[dict]:
    if not performers:
        return [
            {
                "type": "text",
                "text": "データなし",
                "size": "sm",
                "color": COLOR_TEXT_SECONDARY,
                "margin": "md",
            }
        ]
    return [_build_ranking_row(i, p.name, p.symbol, p.change_rate) for i, p in enumerate(performers, 1)]


def _summary_row(label: str, value: str, value_color: str = COLOR_TEXT_PRIMARY) -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "contents": [
            {"type": "text", "text": label, "size": "sm", "color": COLOR_TEXT_SECONDARY},
            {"type": "text", "text": value, "size": "sm", "color": value_color, "align": "end"},
        ],
    }


def _build_summary_contents(portfolio_data: dict[str, Any]) -> list[dict]:
    """資産サマリ部分のFlexコンテンツを作成する"""
    total_cost = _format_currency(portfolio_data["total_cost"])
    total_market_value = _format_currency(portfolio_data["total_market_value"])
    total_pl = _format_currency(portfolio_data["total_pl"])
    total_pl_percentage = _format_decimal(portfolio_data["total_pl_percentage"])
    total_realized_pl = _format_currency(portfolio_data["total_realized_pl"])
    total_dividend = _format_currency(portfolio_data["total_dividend"])

    rows: list[dict] = [
        _summary_row("取得価格", f"{total_cost}円"),
        _summary_row("時価総額", f"{total_market_value}円"),
    ]

    weekly_change = portfolio_data.get("weekly_change")
    if weekly_change is not None:
        formatted_change = _format_currency(abs(weekly_change))
        sign = "+" if weekly_change >= 0 else "-"
        rows.append(
            _summary_row("前週比", f"{sign}{formatted_change}円", _get_profit_loss_color(weekly_change))
        )

    rows.append(
        _summary_row(
            "総損益",
            f"{total_pl}円 ({total_pl_percentage}%)",
            _get_profit_loss_color(float(portfolio_data["total_pl_percentage"])),
        )
    )
    rows.append(_summary_row("実現損益", f"{total_realized_pl}円"))
    rows.append(_summary_row("配当総額", f"{total_dividend}円"))

    return rows


def _build_combined_flex(
    portfolio_data: dict[str, Any],
    top_performers: list,
    bottom_performers: list,
    sections: ChangeReasonSections | None,
) -> dict:
    """資産サマリ・週間騰落ランキング・AI解説を単一バブルにまとめたFlex Messageを作成する"""
    today = now_jst().strftime("%Y/%m/%d")

    separator = {"type": "separator", "margin": "xl", "color": COLOR_SEPARATOR}

    body_contents: list[dict] = [
        _section_heading("資産サマリ"),
        {
            "type": "box",
            "layout": "vertical",
            "margin": "sm",
            "spacing": "sm",
            "contents": _build_summary_contents(portfolio_data),
        },
        separator,
    ]

    if sections:
        body_contents.extend(
            [
                _section_heading("マーケット概況"),
                _section_body(sections.market_overview),
                separator,
            ]
        )

    body_contents.append(_section_heading("上昇トップ5"))
    body_contents.append(
        {"type": "box", "layout": "vertical", "contents": _ranking_contents(top_performers), "margin": "sm"}
    )
    if sections:
        body_contents.append(_section_body(sections.top_commentary, margin="lg"))

    body_contents.append(separator)

    body_contents.append(_section_heading("下落ワースト5"))
    body_contents.append(
        {
            "type": "box",
            "layout": "vertical",
            "contents": _ranking_contents(bottom_performers),
            "margin": "sm",
        }
    )
    if sections:
        body_contents.append(_section_body(sections.bottom_commentary, margin="lg"))

    return {
        "type": "bubble",
        "size": "giga",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "InvestLogix",
                    "weight": "bold",
                    "size": "sm",
                    "color": COLOR_PROFIT,
                },
                {
                    "type": "text",
                    "text": "週次レポート",
                    "weight": "bold",
                    "size": "xl",
                    "margin": "sm",
                    "color": COLOR_HEADING,
                },
                {"type": "text", "text": today, "size": "xs", "color": COLOR_TEXT_MUTED, "margin": "sm"},
            ],
            "paddingAll": "20px",
            "backgroundColor": COLOR_BACKGROUND,
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": body_contents,
            "paddingAll": "20px",
            "backgroundColor": COLOR_BACKGROUND,
        },
    }


async def send_weekly_summary_notification(
    user_id: int,
    portfolio_data: dict[str, Any],
    top_performers: list,
    bottom_performers: list,
    sections: ChangeReasonSections | None,
    db: AsyncSession = None,
) -> bool:
    """資産サマリと週間騰落ランキングを単一Flex Messageで通知する"""
    try:
        line_token = settings.LINE_CHANNEL_ACCESS_TOKEN
        if not line_token:
            logger.error("LINE_CHANNEL_ACCESS_TOKEN が設定されていません")
            return False

        line_user_id = await NotificationService.get_line_user_id(user_id, db)
        if not line_user_id:
            logger.error(f"ユーザーID {user_id} のLINE UserIDが設定されていません")
            return False

        flex_contents = _build_combined_flex(portfolio_data, top_performers, bottom_performers, sections)
        flex_message = {
            "type": "flex",
            "altText": "週次レポート（資産サマリと週間騰落ランキング）",
            "contents": flex_contents,
        }

        headers = {"Authorization": f"Bearer {line_token}", "Content-Type": "application/json"}
        data = {"to": line_user_id, "messages": [flex_message]}

        async with httpx.AsyncClient() as client:
            response = await client.post(LINE_PUSH_URL, headers=headers, json=data)

        if response.status_code == 200:
            logger.info("週次レポートのLINE通知が正常に送信されました")
            return True
        logger.error(f"LINE通知の送信に失敗しました。ステータスコード: {response.status_code}")
        logger.error(f"レスポンス: {response.text}")
        return False

    except Exception as e:
        logger.error(f"LINE通知の送信中にエラーが発生しました: {e!s}")
        return False
