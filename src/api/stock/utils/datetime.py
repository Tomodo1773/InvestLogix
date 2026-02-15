"""日時のタイムゾーン変換ユーティリティ

全APIでリクエスト/レスポンスをJST（日本標準時）で統一するための共通関数を提供します。
"""

from datetime import datetime, timedelta
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


def now_jst() -> datetime:
    """現在のJST時刻を取得する

    Returns:
        JSTタイムゾーン付きの現在時刻
    """
    return datetime.now(JST)


def get_date_range_for_api(days_back: int = 7) -> tuple[str, str]:
    """API用の日付範囲を取得（start_date, end_date）

    日本時間で現在日時と指定日数前の日付範囲を文字列で返します。
    外部APIへのリクエストで使用されることを想定しています。

    Args:
        days_back: 遡る日数（デフォルト: 7日）

    Returns:
        tuple[str, str]: (start_date, end_date) の形式で日付文字列を返す
                         形式: "YYYY-MM-DD"
    """
    now = now_jst()
    end_date = now.strftime("%Y-%m-%d")
    start_date = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")
    return start_date, end_date
