from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Any

from .constants import MONEY_Q
from .utils import to_decimal


@dataclass
class Allocation:
    creditor_id: str
    creditor_name: str
    amount: Decimal


def allocate_proportionally(creditors: list[dict[str, Any]], payment: Decimal) -> tuple[Decimal, list[Allocation]]:
    positive_creditors = [c for c in creditors if to_decimal(c.get("amount", 0)) > 0]
    if not positive_creditors:
        return Decimal("0.00"), []

    debt_cents_by_creditor: dict[str, int] = {}
    name_by_creditor: dict[str, str] = {}
    total_debt_cents = 0

    for creditor in positive_creditors:
        creditor_id = creditor["id"]
        creditor_name = creditor["name"]
        cents = int((to_decimal(creditor["amount"]) * 100).to_integral_value(rounding=ROUND_HALF_UP))
        if cents <= 0:
            continue
        debt_cents_by_creditor[creditor_id] = cents
        name_by_creditor[creditor_id] = creditor_name
        total_debt_cents += cents

    if total_debt_cents <= 0:
        return Decimal("0.00"), []

    requested_cents = int((to_decimal(payment) * 100).to_integral_value(rounding=ROUND_HALF_UP))
    applied_cents = min(requested_cents, total_debt_cents)
    if applied_cents <= 0:
        return Decimal("0.00"), []

    bases: dict[str, int] = {}
    fractions: list[tuple[Decimal, str]] = []
    distributed = 0

    for creditor_id, debt_cents in debt_cents_by_creditor.items():
        raw = Decimal(applied_cents) * Decimal(debt_cents) / Decimal(total_debt_cents)
        base = int(raw.to_integral_value(rounding=ROUND_DOWN))
        bases[creditor_id] = base
        distributed += base
        fractions.append((raw - Decimal(base), creditor_id))

    remaining = applied_cents - distributed
    fractions.sort(key=lambda item: (-item[0], item[1]))

    idx = 0
    while remaining > 0 and idx < len(fractions):
        _, creditor_id = fractions[idx]
        if bases[creditor_id] < debt_cents_by_creditor[creditor_id]:
            bases[creditor_id] += 1
            remaining -= 1
        idx += 1
        if idx == len(fractions) and remaining > 0:
            idx = 0

    allocations = [
        Allocation(
            creditor_id=creditor_id,
            creditor_name=name_by_creditor[creditor_id],
            amount=(Decimal(cents) / Decimal("100")).quantize(MONEY_Q),
        )
        for creditor_id, cents in bases.items()
        if cents > 0
    ]
    allocations.sort(key=lambda a: a.creditor_name.lower())
    applied = (Decimal(applied_cents) / Decimal("100")).quantize(MONEY_Q)
    return applied, allocations
