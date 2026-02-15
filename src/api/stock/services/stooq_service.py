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


def fetch_us_daily_prices_from_stooq(
    symbol: str,
    start_date: DateInput,
    end_date: DateInput,
) -> list[dict]:
    """
    Stooq から米国株の日足データを取得する。
    返却データは日付の昇順（古い順）。
    """
    start = _to_date(start_date)
    end = _to_date(end_date)
    stooq_symbol = _build_stooq_symbol(symbol)
    url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&i=d"

    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
    except Exception as e:
        logger.error(
            "Stooqへのリクエストに失敗しました action=external_io symbol={} error={}",
            symbol,
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
            or row.get("Volume") in (None, "N/D")
        ):
            continue

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
                "volume": int(float(row["Volume"])),
            }
        )

    rows.sort(key=lambda x: x["date"])
    return rows
