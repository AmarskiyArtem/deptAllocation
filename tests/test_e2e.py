from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.store import DebtStore


class DebtAllocationE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.path = Path(self.tmp_dir.name) / "debt_data.json"

    def _open_store(self) -> DebtStore:
        return DebtStore(self.path)

    def test_full_user_flow_with_restart_and_payment_rollback(self) -> None:
        store = self._open_store()

        debtor_id = store.add_debtor("ООО Ромашка")
        creditor_a = store.add_creditor(debtor_id, "Банк A", Decimal("100.00"))
        creditor_b = store.add_creditor(debtor_id, "Банк B", Decimal("50.00"))

        preview_applied, preview_allocations = store.preview_payment(debtor_id, Decimal("30.00"))
        self.assertEqual(preview_applied, Decimal("30.00"))
        self.assertEqual(sum(a.amount for a in preview_allocations), Decimal("30.00"))

        with patch("app.store.now_iso", return_value="2026-02-23T15:00:00"):
            applied, allocations = store.apply_payment(debtor_id, Decimal("30.00"))

        self.assertEqual(applied, Decimal("30.00"))
        self.assertEqual(len(allocations), 2)

        debtor = store.debtor_by_id(debtor_id)
        self.assertIsNotNone(debtor)
        current_by_id = {c["id"]: c["amount"] for c in debtor["creditors"]}
        self.assertEqual(current_by_id[creditor_a], "80.00")
        self.assertEqual(current_by_id[creditor_b], "40.00")
        self.assertEqual(len(debtor["history"]), 1)

        restarted = self._open_store()
        debtor_after_restart = restarted.debtor_by_id(debtor_id)
        self.assertIsNotNone(debtor_after_restart)
        self.assertEqual(len(debtor_after_restart["history"]), 1)
        self.assertEqual(restarted.total_debt(debtor_id), Decimal("120.00"))

        restarted.delete_payment(debtor_id, 0)

        after_delete_restart = self._open_store()
        self.assertEqual(after_delete_restart.total_debt(debtor_id), Decimal("150.00"))
        debtor_final = after_delete_restart.debtor_by_id(debtor_id)
        self.assertIsNotNone(debtor_final)
        self.assertEqual(debtor_final["history"], [])

    def test_payment_larger_than_total_debt_caps_and_closes_debts(self) -> None:
        store = self._open_store()
        debtor_id = store.add_debtor("ИП Тест")
        store.add_creditor(debtor_id, "Кредитор 1", Decimal("12.30"))
        store.add_creditor(debtor_id, "Кредитор 2", Decimal("7.70"))

        with patch("app.store.now_iso", return_value="2026-02-23T15:10:00"):
            applied, allocations = store.apply_payment(debtor_id, Decimal("1000.00"))

        self.assertEqual(applied, Decimal("20.00"))
        self.assertEqual(sum(a.amount for a in allocations), Decimal("20.00"))
        self.assertEqual(store.total_debt(debtor_id), Decimal("0.00"))

        restarted = self._open_store()
        self.assertEqual(restarted.total_debt(debtor_id), Decimal("0.00"))
        debtor = restarted.debtor_by_id(debtor_id)
        self.assertIsNotNone(debtor)
        self.assertEqual(len(debtor["history"]), 1)

    def test_multiple_debtors_do_not_affect_each_other(self) -> None:
        store = self._open_store()
        debtor_a = store.add_debtor("Debtor A")
        debtor_b = store.add_debtor("Debtor B")

        store.add_creditor(debtor_a, "A1", Decimal("25.00"))
        store.add_creditor(debtor_b, "B1", Decimal("40.00"))

        with patch("app.store.now_iso", return_value="2026-02-23T16:00:00"):
            store.apply_payment(debtor_a, Decimal("10.00"))

        restarted = self._open_store()
        self.assertEqual(restarted.total_debt(debtor_a), Decimal("15.00"))
        self.assertEqual(restarted.total_debt(debtor_b), Decimal("40.00"))

        debtor_a_row = restarted.debtor_by_id(debtor_a)
        debtor_b_row = restarted.debtor_by_id(debtor_b)
        self.assertIsNotNone(debtor_a_row)
        self.assertIsNotNone(debtor_b_row)
        self.assertEqual(len(debtor_a_row["history"]), 1)
        self.assertEqual(len(debtor_b_row["history"]), 0)


if __name__ == "__main__":
    unittest.main()
