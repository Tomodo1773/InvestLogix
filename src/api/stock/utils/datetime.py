"""日時のタイムゾーン変換ユーティリティ

全APIでリクエスト/レスポンスをJST（日本標準時）で統一するための共通関数を提供します。
"""

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
UTC = ZoneInfo("UTC")


def to_jst(dt: Optional[datetime]) -> Optional[datetime]:
    """任意のdatetimeをJSTに変換する

    Args:
        dt: 変換対象のdatetime（None可）

    Returns:
        JSTに変換されたdatetime。入力がNoneの場合はNoneを返す。
        naive datetime（タイムゾーン情報なし）の場合はUTCとして扱う。
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(JST)


def from_jst_input(dt: Optional[datetime]) -> Optional[datetime]:
    """リクエストのdatetime（naive想定）をJSTとして解釈する

    Args:
        dt: リクエストから受け取ったdatetime（None可）

    Returns:
        JSTタイムゾーン付きのdatetime。入力がNoneの場合はNoneを返す。
        naive datetime（タイムゾーン情報なし）の場合はJSTとして扱う。
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=JST)
    return dt.astimezone(JST)
