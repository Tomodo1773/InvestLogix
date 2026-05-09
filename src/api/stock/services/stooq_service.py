from __future__ import annotations

import csv
from datetime import date, datetime
from io import StringIO
from typing import Union

import httpx
from loguru import logger

DateInput = Union[str, date, datetime]


def _to_date(value: DateInput) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return datetime.strptime(value, "%Y-%m-%d").date()


def _build_stooq_symbol(symbol: str) -> str:
    normalized = symbol.strip().lower()
    if normalized.endswith(".us"):
        return normalized
    return f"{normalized}.us"


def fetch_daily_prices_from_stooq(
    stooq_symbol: str,
    start_date: DateInput,
    end_date: DateInput,
    *,
    allow_missing_volume: bool = False,
) -> list[dict]:
    """
    Stooq から日足データを取得する汎用関数。
    stooq_symbol はサフィックス処理済みの生シンボル（例: "aapl.us" / "^spx"）。
    指数のようにVolumeが "N/D" になり得るケースは allow_missing_volume=True で 0 扱いする。
    返却データは日付の昇順（古い順）。
    """
    start = _to_date(start_date)
    end = _to_date(end_date)
    url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&i=d"

    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
    except Exception as e:
        logger.error(
            "Stooqへのリクエストに失敗しました action=external_io symbol={} error={}",
            stooq_symbol,
            str(e),
        )
        raise

    rows = []
    reader = csv.DictReader(StringIO(response.text))
    for row in reader:
        if not row or not row.get("Date"):
            continue

        if (
            row.get("Open") in (None, "N/D")
            or row.get("High") in (None, "N/D")
            or row.get("Low") in (None, "N/D")
            or row.get("Close") in (None, "N/D")
        ):
            continue

        volume_raw = row.get("Volume")
        if volume_raw in (None, "N/D"):
            if not allow_missing_volume:
                continue
            volume = 0
        else:
            volume = int(float(volume_raw))

        record_date = datetime.strptime(row["Date"], "%Y-%m-%d").date()
        if record_date < start or record_date > end:
            continue

        rows.append(
            {
                "date": row["Date"],
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": volume,
            }
        )

    rows.sort(key=lambda x: x["date"])
    return rows


def fetch_us_daily_prices_from_stooq(
    symbol: str,
    start_date: DateInput,
    end_date: DateInput,
) -> list[dict]:
    """
    Stooq から米国株の日足データを取得する。
    返却データは日付の昇順（古い順）。
    """
    return fetch_daily_prices_from_stooq(_build_stooq_symbol(symbol), start_date, end_date)
