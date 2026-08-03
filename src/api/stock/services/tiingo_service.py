from __future__ import annotations

from datetime import date, datetime

import httpx
from loguru import logger

from ..database import settings

DateInput = str | date | datetime
TIINGO_BASE_URL = "https://api.tiingo.com/tiingo/daily"


def _to_date_str(value: DateInput) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def fetch_us_daily_prices_from_tiingo(
    symbol: str,
    start_date: DateInput,
    end_date: DateInput,
) -> list[dict]:
    """
    Tiingo から米国株の日足データを取得する。
    調整後価格（adjOpen/adjHigh/adjLow/adjClose/adjVolume）を返却。
    返却データは日付の昇順（Tiingo の仕様）。
    """
    if not settings.TIINGO_API_KEY:
        raise RuntimeError("TIINGO_API_KEY が未設定です")

    ticker = symbol.strip().lower()
    url = f"{TIINGO_BASE_URL}/{ticker}/prices"
    headers = {"Authorization": f"Token {settings.TIINGO_API_KEY}"}
    params = {
        "startDate": _to_date_str(start_date),
        "endDate": _to_date_str(end_date),
        "format": "json",
    }

    try:
        response = httpx.get(url, params=params, headers=headers, timeout=10.0)
        response.raise_for_status()
    except Exception as e:
        logger.error(
            "Tiingoへのリクエストに失敗しました action=external_io symbol={} error={}",
            symbol,
            str(e),
        )
        raise

    return [
        {
            "date": row["date"][:10],
            "open": float(row["adjOpen"]),
            "high": float(row["adjHigh"]),
            "low": float(row["adjLow"]),
            "close": float(row["adjClose"]),
            "volume": int(row["adjVolume"]),
        }
        for row in response.json()
    ]
