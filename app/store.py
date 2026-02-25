from __future__ import annotations

import json
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

from .allocation import Allocation, allocate_proportionally
from .constants import MONEY_Q
from .utils import money_to_str, now_iso, percent_of, to_decimal


class DebtStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: dict[str, Any] = {"version": 1, "debtors": []}
        self.load_error: str | None = self.load()

    def load(self) -> str | None:
        if not self.path.exists():
            return None
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
            if "debtors" not in self.data:
                self.data = {"version": 1, "debtors": []}
            return None
        except (json.JSONDecodeError, OSError):
            self.data = {"version": 1, "debtors": []}
            return f"Не удалось прочитать {self.path.name}. Будет использована пустая база."

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def debtors(self) -> list[dict[str, Any]]:
        return self.data["debtors"]

    def debtor_by_id(self, debtor_id: str) -> dict[str, Any] | None:
        for debtor in self.debtors():
            if debtor["id"] == debtor_id:
                return debtor
        return None

    def add_debtor(self, name: str) -> str:
        debtor_id = str(uuid.uuid4())
        self.debtors().append({"id": debtor_id, "name": name, "creditors": [], "history": []})
        self.save()
        return debtor_id

    def rename_debtor(self, debtor_id: str, new_name: str) -> None:
        debtor = self.debtor_by_id(debtor_id)
        if not debtor:
            return
        debtor["name"] = new_name
        self.save()

    def delete_debtor(self, debtor_id: str) -> None:
        self.data["debtors"] = [d for d in self.debtors() if d["id"] != debtor_id]
        self.save()

    def add_creditor(self, debtor_id: str, name: str, amount: Decimal) -> str:
        debtor = self.debtor_by_id(debtor_id)
        if not debtor:
            raise ValueError("Debtor not found")
        creditor_id = str(uuid.uuid4())
        debtor["creditors"].append({"id": creditor_id, "name": name, "amount": money_to_str(amount)})
        self.save()
        return creditor_id

    def update_creditor(self, debtor_id: str, creditor_id: str, name: str, amount: Decimal) -> None:
        debtor = self.debtor_by_id(debtor_id)
        if not debtor:
            raise ValueError("Debtor not found")
        for creditor in debtor["creditors"]:
            if creditor["id"] == creditor_id:
                creditor["name"] = name
                creditor["amount"] = money_to_str(amount)
                self.save()
                return
        raise ValueError("Creditor not found")

    def delete_creditor(self, debtor_id: str, creditor_id: str) -> None:
        debtor = self.debtor_by_id(debtor_id)
        if not debtor:
            raise ValueError("Debtor not found")
        debtor["creditors"] = [c for c in debtor["creditors"] if c["id"] != creditor_id]
        self.save()

    def total_debt(self, debtor_id: str) -> Decimal:
        debtor = self.debtor_by_id(debtor_id)
        if not debtor:
            return Decimal("0.00")
        total = Decimal("0.00")
        for creditor in debtor["creditors"]:
            total += to_decimal(creditor.get("amount", 0))
        return total.quantize(MONEY_Q)

    def preview_payment(self, debtor_id: str, payment: Decimal) -> tuple[Decimal, list[Allocation]]:
        debtor = self.debtor_by_id(debtor_id)
        if not debtor:
            raise ValueError("Debtor not found")
        return allocate_proportionally(debtor["creditors"], payment)

    def apply_payment(self, debtor_id: str, payment: Decimal) -> tuple[Decimal, list[Allocation]]:
        debtor = self.debtor_by_id(debtor_id)
        if not debtor:
            raise ValueError("Debtor not found")

        applied, allocations = allocate_proportionally(debtor["creditors"], payment)
        if applied <= 0:
            return Decimal("0.00"), []

        total_claims_before_payment = self.total_debt(debtor_id)
        amount_by_creditor = {a.creditor_id: a.amount for a in allocations}
        allocation_meta_by_creditor: dict[str, dict[str, str]] = {}
        for creditor in debtor["creditors"]:
            current = to_decimal(creditor["amount"])
            allocated = amount_by_creditor.get(creditor["id"], Decimal("0.00"))
            new_amount = (current - allocated).quantize(MONEY_Q)
            if new_amount < 0:
                new_amount = Decimal("0.00")
            creditor["amount"] = money_to_str(new_amount)
            if allocated > 0:
                allocation_meta_by_creditor[creditor["id"]] = {
                    "percentage_of_queue": f"{percent_of(allocated, total_claims_before_payment):.2f}",
                    "remaining_claim": money_to_str(new_amount),
                }

        payment_timestamp = now_iso()
        history_row = {
            "timestamp": payment_timestamp,
            "requested_payment": money_to_str(payment),
            "applied_payment": money_to_str(applied),
            "allocations": [
                {
                    "creditor_id": a.creditor_id,
                    "creditor_name": a.creditor_name,
                    "amount": money_to_str(a.amount),
                    "percentage_of_queue": allocation_meta_by_creditor.get(a.creditor_id, {}).get(
                        "percentage_of_queue", "0.00"
                    ),
                    "payment_date": payment_timestamp,
                    "remaining_claim": allocation_meta_by_creditor.get(a.creditor_id, {}).get(
                        "remaining_claim", "0.00"
                    ),
                }
                for a in allocations
            ],
        }
        debtor["history"].insert(0, history_row)
        self.save()
        return applied, allocations

    def delete_payment(self, debtor_id: str, history_index: int) -> None:
        debtor = self.debtor_by_id(debtor_id)
        if not debtor:
            raise ValueError("Debtor not found")
        history = debtor.get("history", [])
        if history_index < 0 or history_index >= len(history):
            raise ValueError("History record not found")

        event = history[history_index]
        creditors = debtor["creditors"]

        for allocation in event.get("allocations", []):
            allocated = to_decimal(allocation.get("amount", 0))
            if allocated <= 0:
                continue

            creditor_id = allocation.get("creditor_id")
            creditor_name = allocation.get("creditor_name", "Неизвестный кредитор")

            target = None
            if creditor_id:
                target = next((c for c in creditors if c["id"] == creditor_id), None)
            if target is None and creditor_name:
                target = next((c for c in creditors if c["name"] == creditor_name), None)

            if target is None:
                creditors.append(
                    {
                        "id": creditor_id or str(uuid.uuid4()),
                        "name": creditor_name,
                        "amount": money_to_str(allocated),
                    }
                )
            else:
                current = to_decimal(target.get("amount", 0))
                target["amount"] = money_to_str((current + allocated).quantize(MONEY_Q))

        del history[history_index]
        self.save()
