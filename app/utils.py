from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from .constants import MONEY_Q, PERCENT_Q


def to_decimal(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_Q, rounding=ROUND_HALF_UP)


def money_to_str(value: Any) -> str:
    return f"{to_decimal(value):.2f}"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def format_datetime_ru(value: str) -> str:
    try:
        dt = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return value
    return dt.strftime("%d.%m.%Y %H:%M:%S")


def percent_of(part: Decimal, total: Decimal) -> Decimal:
    if total <= 0:
        return Decimal("0.00")
    return ((part * Decimal("100")) / total).quantize(PERCENT_Q, rounding=ROUND_HALF_UP)
