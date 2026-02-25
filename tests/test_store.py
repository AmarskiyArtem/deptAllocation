from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.store import DebtStore


class DebtStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.path = Path(self.tmp_dir.name) / "debt_data.json"
        self.store = DebtStore(self.path)

    def test_initializes_empty_store_when_file_missing(self) -> None:
        self.assertIsNone(self.store.load_error)
        self.assertEqual(self.store.debtors(), [])

    def test_load_returns_error_for_invalid_json(self) -> None:
        self.path.write_text("{", encoding="utf-8")
        store = DebtStore(self.path)
        self.assertIsNotNone(store.load_error)
        self.assertEqual(store.debtors(), [])

    def test_debtor_and_creditor_crud_and_total(self) -> None:
        debtor_id = self.store.add_debtor("Alice")
        self.store.rename_debtor(debtor_id, "Alice 2")
        creditor_id = self.store.add_creditor(debtor_id, "Bank", Decimal("10.20"))
        self.store.update_creditor(debtor_id, creditor_id, "Bank 2", Decimal("7.00"))

        debtor = self.store.debtor_by_id(debtor_id)
        self.assertIsNotNone(debtor)
        self.assertEqual(debtor["name"], "Alice 2")
        self.assertEqual(self.store.total_debt(debtor_id), Decimal("7.00"))

        self.store.delete_creditor(debtor_id, creditor_id)
        self.assertEqual(self.store.total_debt(debtor_id), Decimal("0.00"))

        self.store.delete_debtor(debtor_id)
        self.assertIsNone(self.store.debtor_by_id(debtor_id))

    def test_apply_payment_updates_balances_and_history(self) -> None:
        debtor_id = self.store.add_debtor("Bob")
        creditor_a = self.store.add_creditor(debtor_id, "A", Decimal("10.00"))
        creditor_b = self.store.add_creditor(debtor_id, "B", Decimal("20.00"))

        with patch("app.store.now_iso", return_value="2026-02-23T12:34:56"):
            applied, allocations = self.store.apply_payment(debtor_id, Decimal("15.00"))

        self.assertEqual(applied, Decimal("15.00"))
        self.assertEqual(sum(a.amount for a in allocations), Decimal("15.00"))

        debtor = self.store.debtor_by_id(debtor_id)
        self.assertIsNotNone(debtor)

        by_id = {c["id"]: c["amount"] for c in debtor["creditors"]}
        self.assertEqual(by_id[creditor_a], "5.00")
        self.assertEqual(by_id[creditor_b], "10.00")

        history = debtor["history"]
        self.assertEqual(len(history), 1)
        row = history[0]
        self.assertEqual(row["timestamp"], "2026-02-23T12:34:56")
        self.assertEqual(row["requested_payment"], "15.00")
        self.assertEqual(row["applied_payment"], "15.00")
        self.assertEqual(len(row["allocations"]), 2)
        self.assertTrue(all(a["percentage_of_queue"] != "0.00" for a in row["allocations"]))
        self.assertTrue(all(a["payment_date"] == "2026-02-23T12:34:56" for a in row["allocations"]))

    def test_apply_payment_returns_zero_for_empty_debts(self) -> None:
        debtor_id = self.store.add_debtor("No debt")
        applied, allocations = self.store.apply_payment(debtor_id, Decimal("10.00"))
        self.assertEqual(applied, Decimal("0.00"))
        self.assertEqual(allocations, [])

    def test_delete_payment_restores_amounts_and_removes_history(self) -> None:
        debtor_id = self.store.add_debtor("Carol")
        self.store.add_creditor(debtor_id, "A", Decimal("10.00"))
        self.store.add_creditor(debtor_id, "B", Decimal("20.00"))

        with patch("app.store.now_iso", return_value="2026-02-23T12:34:56"):
            self.store.apply_payment(debtor_id, Decimal("9.00"))

        debtor = self.store.debtor_by_id(debtor_id)
        self.assertIsNotNone(debtor)
        self.assertEqual(len(debtor["history"]), 1)

        self.store.delete_payment(debtor_id, 0)
        debtor = self.store.debtor_by_id(debtor_id)
        self.assertEqual(len(debtor["history"]), 0)

        restored_total = self.store.total_debt(debtor_id)
        self.assertEqual(restored_total, Decimal("30.00"))

    def test_delete_payment_recreates_missing_creditor(self) -> None:
        debtor_id = self.store.add_debtor("D")
        creditor_id = self.store.add_creditor(debtor_id, "Lost", Decimal("10.00"))

        with patch("app.store.now_iso", return_value="2026-02-23T12:34:56"):
            self.store.apply_payment(debtor_id, Decimal("5.00"))

        self.store.delete_creditor(debtor_id, creditor_id)
        debtor = self.store.debtor_by_id(debtor_id)
        self.assertEqual(len(debtor["creditors"]), 0)

        self.store.delete_payment(debtor_id, 0)
        debtor = self.store.debtor_by_id(debtor_id)
        recreated = debtor["creditors"]
        self.assertEqual(len(recreated), 1)
        self.assertEqual(recreated[0]["id"], creditor_id)
        self.assertEqual(recreated[0]["name"], "Lost")
        self.assertEqual(recreated[0]["amount"], "5.00")

    def test_raises_for_missing_entities(self) -> None:
        with self.assertRaises(ValueError):
            self.store.add_creditor("missing", "X", Decimal("1.00"))
        with self.assertRaises(ValueError):
            self.store.preview_payment("missing", Decimal("1.00"))
        with self.assertRaises(ValueError):
            self.store.apply_payment("missing", Decimal("1.00"))
        with self.assertRaises(ValueError):
            self.store.delete_payment("missing", 0)


if __name__ == "__main__":
    unittest.main()
