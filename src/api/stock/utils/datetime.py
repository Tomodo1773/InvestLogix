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


def from_jst_input(dt_input: Optional[str | datetime]) -> Optional[datetime]:
    """リクエストのdatetime入力をJSTとして解釈する

    Pydanticバリデータの mode="before" で使用することを想定。
    JSON文字列から読み込んだISO形式のdatetime文字列、または
    Pythonコードから直接渡されたdatetimeオブジェクトを、JSTタイムゾーン付きのdatetimeに変換する。

    Args:
        dt_input: ISO形式のdatetime文字列またはdatetimeオブジェクト（None可）
                  例: "2024-01-01T00:00:00" (naive文字列)
                      "2024-01-01T00:00:00Z" (UTC文字列)
                      datetime(2024, 1, 1, 0, 0, 0) (naive datetime)
                      datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC) (timezone-aware datetime)

    Returns:
        JSTタイムゾーン付きのdatetime。入力がNoneの場合はNoneを返す。
        タイムゾーン情報がない場合（naive）はJSTとして扱う。
        タイムゾーン情報がある場合はJSTに変換する。
    """
    if dt_input is None:
        return None

    # 既にdatetimeオブジェクトの場合はそのまま使用
    if isinstance(dt_input, datetime):
        dt = dt_input
    else:
        # ISO形式文字列をdatetimeに変換
        dt = datetime.fromisoformat(dt_input)

    # タイムゾーン情報がない場合はJSTとして扱う
    if dt.tzinfo is None:
        return dt.replace(tzinfo=JST)

    # タイムゾーン情報がある場合はJSTに変換
    return dt.astimezone(JST)
