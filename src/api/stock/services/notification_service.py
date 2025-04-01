import logging
import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

import httpx
import pytz
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models

# 環境変数のロード
load_dotenv()

logger = logging.getLogger(__name__)


class NotificationService:
    """LINE通知サービス"""

    @staticmethod
    async def send_line_notification(user_id: int, portfolio_data: Dict[str, Any], db: AsyncSession = None) -> bool:
        """
        ポートフォリオ情報をLINEに通知する

        Args:
            user_id (int): ユーザーID
            portfolio_data (Dict[str, Any]): 通知するポートフォリオデータ
            db (AsyncSession, optional): データベースセッション。指定がない場合は環境変数のLINE_USER_IDを使用

        Returns:
            bool: 通知が成功したかどうか
        """
        try:
            # LINE APIの設定
            line_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

            if not line_token:
                logger.error("LINE_CHANNEL_ACCESS_TOKEN が設定されていません")
                return False

            # ユーザーのLINE UserIDを取得
            line_user_id = await NotificationService.get_line_user_id(user_id, db)

            if not line_user_id:
                logger.error(f"ユーザーID {user_id} のLINE UserIDが設定されていません")
                return False

            # 日本時間の現在時刻
            current_time = datetime.now(pytz.timezone("Asia/Tokyo"))
            today = current_time.strftime("%Y/%m/%d")

            # ポートフォリオデータのフォーマット
            total_cost = _format_currency(portfolio_data["total_cost"])
            total_market_value = _format_currency(portfolio_data["total_market_value"])
            total_unrealized_pl = _format_currency(portfolio_data["total_unrealized_pl"])
            total_unrealized_pl_percentage = _format_decimal(portfolio_data["total_unrealized_pl_percentage"])
            total_realized_pl = _format_currency(portfolio_data["total_realized_pl"])
            total_dividend = _format_currency(portfolio_data["total_dividend"])

            # 損益に応じたコメント
            comment = _generate_comment(portfolio_data["total_unrealized_pl_percentage"])

            # LINEのFlex Message作成
            flex_contents = {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "InvestLogix",
                                    "weight": "bold",
                                    "color": "#1DB446",
                                    "size": "sm",
                                    "align": "start",
                                }
                            ],
                        },
                        {"type": "text", "text": "資産サマリ", "weight": "bold", "size": "xxl", "margin": "md"},
                        {"type": "text", "text": today, "size": "xs", "color": "#aaaaaa", "wrap": True},
                        {"type": "separator", "margin": "xxl"},
                        {
                            "type": "box",
                            "layout": "vertical",
                            "margin": "xxl",
                            "spacing": "sm",
                            "contents": [
                                {"type": "text", "text": "資産情報", "weight": "bold"},
                                {
                                    "type": "box",
                                    "layout": "horizontal",
                                    "margin": "sm",
                                    "contents": [
                                        {"type": "text", "text": "取得価格", "size": "sm", "color": "#555555"},
                                        {
                                            "type": "text",
                                            "size": "sm",
                                            "color": "#111111",
                                            "align": "end",
                                            "text": f"{total_cost}円",
                                        },
                                    ],
                                },
                                {
                                    "type": "box",
                                    "layout": "horizontal",
                                    "contents": [
                                        {"type": "text", "text": "時価総額", "size": "sm", "color": "#555555"},
                                        {
                                            "type": "text",
                                            "text": f"{total_market_value}円",
                                            "size": "sm",
                                            "color": "#111111",
                                            "align": "end",
                                        },
                                    ],
                                },
                                {
                                    "type": "box",
                                    "layout": "horizontal",
                                    "contents": [
                                        {"type": "text", "text": "評価損益", "size": "sm", "color": "#555555"},
                                        {
                                            "type": "text",
                                            "text": f"{total_unrealized_pl}円 ({total_unrealized_pl_percentage}%)",
                                            "size": "sm",
                                            "color": _get_profit_loss_color(
                                                float(portfolio_data["total_unrealized_pl_percentage"])
                                            ),
                                            "align": "end",
                                        },
                                    ],
                                },
                                {
                                    "type": "box",
                                    "layout": "horizontal",
                                    "contents": [
                                        {"type": "text", "text": "実現損益", "size": "sm", "color": "#555555"},
                                        {
                                            "type": "text",
                                            "text": f"{total_realized_pl}円",
                                            "size": "sm",
                                            "color": "#111111",
                                            "align": "end",
                                        },
                                    ],
                                },
                                {
                                    "type": "box",
                                    "layout": "horizontal",
                                    "contents": [
                                        {"type": "text", "text": "配当総額", "size": "sm", "color": "#555555"},
                                        {
                                            "type": "text",
                                            "text": f"{total_dividend}円",
                                            "size": "sm",
                                            "color": "#111111",
                                            "align": "end",
                                        },
                                    ],
                                },
                            ],
                        },
                        {"type": "separator", "margin": "xxl"},
                        {
                            "type": "box",
                            "layout": "vertical",
                            "margin": "md",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "アドバイザーコメント",
                                    "size": "xs",
                                    "color": "#111111",
                                    "flex": 0,
                                    "weight": "bold",
                                },
                                {
                                    "type": "text",
                                    "text": comment,
                                    "color": "#111111",
                                    "size": "xs",
                                    "align": "start",
                                    "margin": "sm",
                                    "wrap": True,
                                },
                            ],
                        },
                    ],
                },
                "styles": {"footer": {"separator": True}},
            }

            flex_message = {"type": "flex", "altText": "ポートフォリオの更新情報をお知らせします", "contents": flex_contents}

            headers = {"Authorization": f"Bearer {line_token}", "Content-Type": "application/json"}

            data = {"to": line_user_id, "messages": [flex_message]}

            # LINE Message APIにリクエストを送信
            async with httpx.AsyncClient() as client:
                response = await client.post("https://api.line.me/v2/bot/message/push", headers=headers, json=data)

            # レスポンス処理
            if response.status_code == 200:
                logger.info("LINE通知が正常に送信されました")
                return True
            else:
                logger.error(f"LINE通知の送信に失敗しました。ステータスコード: {response.status_code}")
                logger.error(f"レスポンス: {response.text}")
                return False

        except Exception as e:
            logger.error(f"LINE通知の送信中にエラーが発生しました: {str(e)}")
            return False

    @staticmethod
    async def get_line_user_id(user_id: int, db: AsyncSession = None) -> Optional[str]:
        """
        指定されたユーザーIDに対応するLINE UserIDを取得する

        Args:
            user_id (int): ユーザーID
            db (AsyncSession, optional): データベースセッション

        Returns:
            Optional[str]: LINE UserID。設定されていない場合はNone
        """
        # DBセッションが渡されていない場合はNoneを返す
        if db is None:
            return None

        # データベースからユーザー情報を取得
        query = select(models.User).where(models.User.user_id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user or not user.line_user_id:
            # ユーザーが存在しないか、LINE UserIDが設定されていない場合
            return None

        return user.line_user_id


def _format_currency(value: Decimal) -> str:
    """通貨表示用のフォーマット"""
    if value is None:
        return "0"
    return f"{int(value):,}"


def _format_decimal(value: Decimal) -> str:
    """小数表示用のフォーマット"""
    if value is None:
        return "0.00"
    return f"{float(value):.2f}"


def _get_profit_loss_color(percentage: float) -> str:
    """損益率に応じた表示色を返す"""
    if percentage > 0:
        return "#1DB446"  # 利益の場合は緑
    elif percentage < 0:
        return "#DB2C2C"  # 損失の場合は赤
    else:
        return "#111111"  # ゼロの場合は黒


def _generate_comment(percentage: float) -> str:
    """損益率に応じたコメントを生成"""
    if percentage >= 40:
        return "非常に高いリターンを達成しています！継続的な投資戦略が実を結んでいます"
    elif percentage >= 35:
        return "素晴らしい成績です！長期投資の効果が出ています"
    elif percentage >= 30:
        return "良好なパフォーマンスを維持しています。このまま継続しましょう"
    elif percentage >= 25:
        return "堅実な成長を続けています。投資方針は正しいようです"
    elif percentage >= 20:
        return "着実な成長を見せています。この調子で継続していきましょう"
    elif percentage >= 10:
        return "順調なリターンを維持しています。長期的な視点を忘れずに"
    else:
        return "市場環境に応じて慎重に判断し、投資方針を見直してみましょう"
